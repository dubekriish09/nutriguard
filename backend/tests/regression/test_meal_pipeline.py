import uuid
import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.orm import Session
from models.user import User, UserProfile, UserCondition, UserMedication, UserAllergy
from models.condition import Condition
from models.medication import Medication
from models.food import Allergen
from core import security
from api.deps import get_db

client = TestClient(app)

def create_and_auth_user(profile_data: dict) -> tuple[str, dict]:
    # We will grab a db session
    db: Session = next(app.dependency_overrides.get(get_db, get_db)())
    
    # 1. Create User
    user = User(email=profile_data["email"], hashed_password=security.get_password_hash("TestPass123!"), display_name=profile_data["name"])
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = str(user.user_id)
    
    # 2. Create Profile
    pd = profile_data["profile"]
    prof = UserProfile(
        user_id=user.user_id,
        age=pd.get("age", 30),
        sex=pd.get("sex", "female"),
        weight_kg=pd.get("weight_kg", 70),
        height_cm=pd.get("height_cm", 170),
        activity_level=pd.get("activity_level", "sedentary"),
        dietary_pattern=pd.get("dietary_pattern", "vegetarian")
    )
    db.add(prof)
    
    # 3. Create Conditions
    for c_data in profile_data.get("conditions", []):
        c_name = c_data["condition_name"].replace('_', ' ')
        c = db.query(Condition).filter(Condition.name.ilike(f"%{c_name}%")).first()
        if not c:
            c = Condition(name=c_name)
            db.add(c)
            db.commit()
            db.refresh(c)
        uc = UserCondition(user_id=user.user_id, condition_id=c.condition_id, lab_values=c_data.get("lab_values", {}))
        db.add(uc)
        
    # 4. Medications
    for m_data in profile_data.get("medications", []):
        m_name = m_data["medication_name"].replace('_', ' ')
        m = db.query(Medication).filter(Medication.generic_name.ilike(f"%{m_name}%")).first()
        if not m:
            m = Medication(generic_name=m_name, drug_class='Mock Class')
            db.add(m)
            db.commit()
            db.refresh(m)
        um = UserMedication(user_id=user.user_id, medication_id=m.medication_id, timing_relative_to_meal=m_data.get("timing_relative_to_meal"))
        if "dose_amount" in m_data:
            um.dose_amount = m_data["dose_amount"]
        if "dose_unit" in m_data:
            um.dose_unit = m_data["dose_unit"]
        db.add(um)
        
    # 5. Allergies
    for a_data in profile_data.get("allergies", []):
        a_name = a_data["allergen_name"]
        a = db.query(Allergen).filter(Allergen.name.ilike(f"%{a_name}%")).first()
        if not a:
            a = Allergen(name=a_name)
            db.add(a)
            db.commit()
            db.refresh(a)
        ua = UserAllergy(user_id=user.user_id, allergen_id=a.allergen_id)
        db.add(ua)
        
    db.commit()
    
    token = security.create_access_token(user.user_id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, headers

def sum_meal_sodium(meals: dict) -> float:
    total = 0.0
    for meal in meals.values():
        total += meal.get("total_nutrition", {}).get("sodium_mg", 0)
    return total

def sum_meal_sat_fat(meals: dict) -> float:
    total = 0.0
    for meal in meals.values():
        total += meal.get("total_nutrition", {}).get("sat_fat_g", 0)
    return total

def get_all_foods_in_plan(meals: dict) -> list[str]:
    foods = []
    for meal in meals.values():
        for food in meal.get("foods", []):
            foods.append(food["food_name"].lower())
    return foods

def test_profile_1_meal_plan():
    user_id, headers = create_and_auth_user({
        "email": f"profile1_{uuid.uuid4()}@test.com",
        "name": "Profile 1",
        "profile": {
            "age": 52, "sex": "female",
            "weight_kg": 60, "height_cm": 158,
            "activity_level": "sedentary",
            "dietary_pattern": "vegetarian"
        },
        "conditions": [
            {"condition_name": "type_2_diabetes"},
            {"condition_name": "hypertension"}
        ],
        "medications": [
            {"medication_name": "metformin",
             "dose_amount": 500, "dose_unit": "mg",
             "frequency": "twice_daily",
             "timing_relative_to_meal": "with_food"},
            {"medication_name": "telmisartan",
             "dose_amount": 40, "dose_unit": "mg",
             "frequency": "once_daily"}
        ]
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    plan = r.json()

    assert "meals" in plan
    assert "medication_timing" in plan
    assert "nutrient_gaps" in plan
    assert "targets" in plan
    assert len(plan["meals"]) == 5, "Must have 5 meal types"

    assert sum_meal_sodium(plan["meals"]) < 1500, "Total sodium must be under 1500mg"
    assert plan["targets"]["added_sugar_g"] == 0, "No added sugar for diabetic profile"
    assert plan["targets"]["prioritize_low_gi"] == True, "Low-GI flag must be set"

    timing_meds = [t["medication_name"].lower() for t in plan["medication_timing"]]
    assert "metformin" in timing_meds, "Metformin must appear in timing advice"
    metformin_timing = next(t for t in plan["medication_timing"] if "metformin" in t["medication_name"].lower())
    assert "food" in metformin_timing["meal_association"].lower(), "Metformin must be assigned with a meal"

    depletion_nutrients = [
        f["nutrient"] for f in plan["nutrient_gaps"]["depletion_flags"] if isinstance(f, dict)
    ]
    assert "vitamin_b12" in depletion_nutrients, "Metformin B12 depletion must be flagged"

    food_names = get_all_foods_in_plan(plan["meals"])
    blocked_foods = ["samosa", "jalebi", "gulab jamun", "namkeen"]
    for blocked in blocked_foods:
        assert blocked not in food_names, f"{blocked} must not appear in diabetic/hypertensive plan"

    assert plan["safety_validated"] == True

def test_profile_2_ckd_anemia():
    user_id, headers = create_and_auth_user({
        "email": f"profile2_{uuid.uuid4()}@test.com",
        "name": "Profile 2",
        "profile": {
            "age": 68, "sex": "male",
            "weight_kg": 72, "height_cm": 168,
            "activity_level": "sedentary",
            "dietary_pattern": "non_vegetarian"
        },
        "conditions": [
            {"condition_name": "ckd", "lab_values": {"egfr": 38}},
            {"condition_name": "hypertension"},
            {"condition_name": "iron_def_anemia"}
        ],
        "medications": [
            {"medication_name": "ferrous_sulfate",
             "timing_relative_to_meal": "before_food"},
            {"medication_name": "calcium_carbonate",
             "timing_relative_to_meal": "with_food"},
            {"medication_name": "amlodipine"}
        ]
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200
    plan = r.json()

    assert plan["targets"]["restrict_potassium"] == False, "Potassium must NOT be restricted at CKD Stage 3 (eGFR 38)"
    assert plan["targets"]["restrict_protein"] == True
    max_protein = 0.6 * 72   # 43.2g
    assert plan["targets"]["protein_g"] <= max_protein + 1.0, f"Protein must be <= {max_protein}g for CKD"

    warnings = []
    for timing in plan["medication_timing"]:
        warnings.extend(timing.get("warnings", []))
    warning_text = " ".join(warnings).lower()
    assert "iron" in warning_text and "calcium" in warning_text, "Iron-calcium timing conflict must be warned"

    food_names = get_all_foods_in_plan(plan["meals"])
    iron_rich = ["rajma", "ragi", "palak", "amaranth", "drumstick", "chana"]
    assert any(iron in food_names for iron in iron_rich), "At least one iron-rich food must be in the plan"

def test_profile_3_hypothyroid_gout_jain():
    user_id, headers = create_and_auth_user({
        "email": f"profile3_{uuid.uuid4()}@test.com",
        "name": "Profile 3",
        "profile": {
            "age": 35, "sex": "male",
            "weight_kg": 80, "height_cm": 175,
            "activity_level": "lightly_active",
            "dietary_pattern": "jain"
        },
        "conditions": [
            {"condition_name": "hypothyroidism"},
            {"condition_name": "gout"}
        ],
        "medications": [
            {"medication_name": "levothyroxine",
             "dose_amount": 50, "dose_unit": "mcg",
             "frequency": "once_daily",
             "timing_relative_to_meal": "before_food"}
        ]
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200
    plan = r.json()

    food_names = get_all_foods_in_plan(plan["meals"])
    assert "onion" not in food_names, "Onion must be excluded (Jain)"
    assert "garlic" not in food_names, "Garlic must be excluded (Jain)"

    high_purine = ["mutton", "masoor dal", "prawns", "organ"]
    for food in high_purine:
        assert food not in food_names, f"{food} must be blocked (Gout - high purine)"

    timing_meds = [t["medication_name"].lower() for t in plan["medication_timing"]]
    assert "levothyroxine" in timing_meds
    levo_timing = next(t for t in plan["medication_timing"] if "levothyroxine" in t["medication_name"].lower())
    assert "before" in levo_timing["meal_association"].lower() or "empty" in levo_timing["instruction"].lower(), "Levothyroxine must be flagged as before_breakfast/empty_stomach"

    assert plan["targets"]["restrict_purines"] == True

def test_profile_4_vegan_anemia_pcos():
    user_id, headers = create_and_auth_user({
        "email": f"profile4_{uuid.uuid4()}@test.com",
        "name": "Profile 4",
        "profile": {
            "age": 28, "sex": "female",
            "weight_kg": 55, "height_cm": 162,
            "activity_level": "moderately_active",
            "dietary_pattern": "vegan"
        },
        "conditions": [
            {"condition_name": "iron_def_anemia"},
            {"condition_name": "pcos"}
        ],
        "medications": []
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200
    plan = r.json()

    food_names = get_all_foods_in_plan(plan["meals"])
    animal_foods = ["chicken", "mutton", "egg", "fish", "milk", "curd", "paneer", "ghee", "butter", "dahi"]
    for animal in animal_foods:
        assert animal not in food_names, f"{animal} must be excluded (Vegan)"

    plant_iron = ["rajma", "ragi", "tofu", "pumpkin seeds", "amaranth", "chana", "palak"]
    assert any(food in food_names for food in plant_iron), "At least one plant iron source must be present"
    assert plan["targets"]["prioritize_low_gi"] == True
    assert plan["targets"]["iron_mg"] >= 30, "Iron target must be therapeutic for female anemia"

    vit_c_foods = ["amla", "guava", "lemon", "orange", "tomato"]
    assert any(food in food_names for food in vit_c_foods), "Vitamin C source must be present to aid iron absorption"

def test_profile_5_hyperlipidemia_gerd():
    user_id, headers = create_and_auth_user({
        "email": f"profile5_{uuid.uuid4()}@test.com",
        "name": "Profile 5",
        "profile": {
            "age": 45, "sex": "male",
            "weight_kg": 85, "height_cm": 172,
            "activity_level": "lightly_active",
            "dietary_pattern": "non_vegetarian"
        },
        "conditions": [
            {"condition_name": "hyperlipidemia"},
            {"condition_name": "gerd"}
        ],
        "medications": [
            {"medication_name": "atorvastatin",
             "timing_relative_to_meal": "with_food",
             "frequency": "once_daily"},
            {"medication_name": "pantoprazole",
             "timing_relative_to_meal": "before_food",
             "frequency": "once_daily"}
        ]
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200
    plan = r.json()

    total_calories = plan["targets"]["calories_kcal"]
    sat_fat_ceiling = (total_calories * 0.07) / 9
    actual_sat_fat = sum_meal_sat_fat(plan["meals"])
    assert actual_sat_fat <= sat_fat_ceiling + 1.0, f"Sat fat {actual_sat_fat}g exceeds 7% ceiling {sat_fat_ceiling}g"

    assert plan["targets"]["small_frequent_meals"] == True
    assert plan["targets"]["avoid_late_dinner"] == True

    dinner_rationale = " ".join(plan["meals"].get("dinner", {}).get("rationale", [])).lower()
    assert "gerd" in dinner_rationale or "sleep" in dinner_rationale or "2" in dinner_rationale, "Dinner must include GERD timing warning"

    atorvastatin_timing = next((t for t in plan["medication_timing"] if "atorvastatin" in t["medication_name"].lower()), None)
    assert atorvastatin_timing is not None
    assert "dinner" in atorvastatin_timing["meal_association"].lower() or "evening" in atorvastatin_timing["meal_association"].lower(), "Atorvastatin must be assigned to dinner/evening"

    panto_timing = next((t for t in plan["medication_timing"] if "pantoprazole" in t["medication_name"].lower()), None)
    assert panto_timing is not None
    assert "breakfast" in panto_timing["meal_association"].lower() or "before" in panto_timing["instruction"].lower(), "Pantoprazole must be before breakfast"

    food_names = get_all_foods_in_plan(plan["meals"])
    fried = ["samosa", "pakora", "puri", "bhatura", "chakli"]
    for f in fried:
        assert f not in food_names, f"{f} must not appear (GERD + Hyperlipidemia)"

    depletion_nutrients = [d["nutrient"] for d in plan["nutrient_gaps"].get("depletion_flags", []) if isinstance(d, dict)]
    assert "coq10" in depletion_nutrients, "Statin CoQ10 depletion must be flagged"

def test_safety_engine_cannot_be_overridden():
    user_id, headers = create_and_auth_user({
        "email": f"safety_test_{uuid.uuid4()}@test.com",
        "name": "Safety Test",
        "profile": {
            "age": 40, "sex": "male",
            "weight_kg": 70, "activity_level": "sedentary",
            "dietary_pattern": "vegetarian"
        },
        "conditions": [{"condition_name": "hypertension"}],
        "medications": [],
        "allergies": [{"allergen_name": "peanuts"}]
    })

    r = client.post("/api/v1/recommendations/meals/generate", headers=headers)
    assert r.status_code == 200
    plan = r.json()

    food_names = get_all_foods_in_plan(plan["meals"])
    assert "peanuts" not in food_names, "Peanut allergy must block peanuts from all meals"
    assert plan["safety_validated"] == True
