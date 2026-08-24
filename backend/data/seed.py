import json
import os
import sys
from uuid import uuid4

# Add parent directory to path so we can import from core and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from core.security import get_password_hash
from models.user import User
from models.food import Food, Nutrient, Allergen, FoodNutrition
from models.medication import Medication, DrugFoodInteraction, DrugNutrientDepletion
from models.condition import Condition, ConditionNutritionRule
from models.evidence import DataSource, Evidence, RuleEvidence

def normalize_name(name: str) -> str:
    return name.lower().strip().replace(' ', '_').replace('-', '_')

def seed_users(db):
    users = [
        {"email": "admin@nutriguard.com", "role": "ADMIN", "display_name": "System Admin"},
        {"email": "reviewer@nutriguard.com", "role": "CLINICAL_REVIEWER", "display_name": "Clinical Reviewer"},
        {"email": "user@nutriguard.com", "role": "USER", "display_name": "Test User"}
    ]
    for u in users:
        existing = db.query(User).filter_by(email=u["email"]).first()
        if not existing:
            user = User(
                email=u["email"],
                hashed_password=get_password_hash("password123"),
                role=u["role"],
                display_name=u["display_name"]
            )
            db.add(user)
    db.flush()

def seed_foods(db, foods_data):
    # Track created nutrients to avoid duplicate creation in same run
    nutrient_cache = {}
    
    for item in foods_data:
        # Check if food exists (idempotency)
        existing = db.query(Food).filter_by(name=item['name']).first()
        if existing:
            # Seed missing allergens even if food exists
            for alg_name in item.get('allergens', []):
                alg_name_lower = alg_name.lower()
                alg = db.query(Allergen).filter_by(name=alg_name_lower).first()
                if not alg:
                    alg = Allergen(name=alg_name_lower)
                    db.add(alg)
                    db.flush()
                
                from models.food import FoodAllergen
                existing_fa = db.query(FoodAllergen).filter_by(food_id=existing.food_id, allergen_id=alg.allergen_id).first()
                if not existing_fa:
                    db.add(FoodAllergen(food_id=existing.food_id, allergen_id=alg.allergen_id))
            continue
            
        food = Food(
            name=item['name'],
            aliases=item.get('aliases', []),
            category=item['category'],
            subcategory=item.get('subcategory'),
            cuisine_origin=item.get('cuisine_origin', []),
            description=item.get('description'),
            is_raw=item.get('is_raw', True),
            is_vegetarian=item.get('is_vegetarian', True),
            is_vegan=item.get('is_vegan', False),
            is_jain=item.get('is_jain', False),
            is_gluten_free=item.get('is_gluten_free', False),
            is_lactose_free=item.get('is_lactose_free', False),
            glycemic_index=item.get('glycemic_index'),
            purine_level=item.get('purine_level'),
            vitamin_k_mcg=item.get('vitamin_k_mcg'),
            nutrient_source=item.get('nutrient_source')
        )
        db.add(food)
        db.flush() # flush to get food_id generated
        
        for n_data in item.get('nutrients', []):
            n_name = n_data['name']
            if n_name not in nutrient_cache:
                nutrient = db.query(Nutrient).filter_by(name=n_name).first()
                if not nutrient:
                    nutrient = Nutrient(name=n_name, unit=n_data['unit'])
                    db.add(nutrient)
                    db.flush()
                nutrient_cache[n_name] = nutrient.nutrient_id
                
            fn = FoodNutrition(
                food_id=food.food_id,
                nutrient_id=nutrient_cache[n_name],
                amount=n_data['amount'],
                unit=n_data['unit']
            )
            db.add(fn)
            
        for alg_name in item.get('allergens', []):
            alg_name_lower = alg_name.lower()
            alg = db.query(Allergen).filter_by(name=alg_name_lower).first()
            if not alg:
                alg = Allergen(name=alg_name_lower)
                db.add(alg)
                db.flush()
            
            from models.food import FoodAllergen
            fa = FoodAllergen(food_id=food.food_id, allergen_id=alg.allergen_id)
            db.add(fa)

def seed_medications(db, meds_data):
    for item in meds_data:
        existing = db.query(Medication).filter_by(generic_name=item['generic_name']).first()
        if existing:
            continue
            
        med = Medication(
            generic_name=normalize_name(item['generic_name']),
            brand_names=item.get('brand_names', []),
            drug_class=item['drug_class'],
            indications=item.get('indications', []),
            dosage_forms=item.get('dosage_forms', []),
            route=item.get('route', []),
            standard_timing=item.get('standard_timing'),
            timing_category=item.get('timing_category'),
            contraindications=item.get('contraindications', []),
            warnings=item.get('warnings', [])
        )
        db.add(med)
        db.flush()
        
        for inter in item.get('interactions', []):
            dfi = DrugFoodInteraction(
                medication_id=med.medication_id,
                interaction_type=inter['interaction_type'],
                food_category=inter.get('food_category'),
                food_component=inter.get('food_component') or inter.get('nutrient'),
                severity=inter['severity'],
                direction=inter.get('direction'),
                mechanism=inter['mechanism'],
                effect=inter.get('effect', 'Unknown'),
                recommendation=inter['recommendation'],
                timing_window=inter.get('timing_window'),
                quantity_threshold=inter.get('quantity_threshold')
            )
            db.add(dfi)
            
        for dep in item.get('depletions', []):
            # In a real system, look up Nutrient ID here
            pass

def seed_conditions(db, conditions_data):
    for item in conditions_data:
        existing = db.query(Condition).filter_by(name=item['name']).first()
        if existing:
            continue
            
        cond = Condition(
            name=normalize_name(item['name']),
            aliases=item.get('aliases', []),
            category=item.get('category'),
            description=item.get('description'),
            relevant_parameters=item.get('parameters', [])
        )
        db.add(cond)
        db.flush()
        
        for rule in item.get('nutrition_rules', []):
            # Find nutrient
            nutrient_name = rule.get('nutrient')
            nutrient_id = None
            if nutrient_name:
                n = db.query(Nutrient).filter_by(name=nutrient_name).first()
                if not n:
                    n = Nutrient(name=nutrient_name, unit='mg')
                    db.add(n)
                    db.flush()
                nutrient_id = n.nutrient_id
                
            cnr = ConditionNutritionRule(
                condition_id=cond.condition_id,
                action=rule['action'],
                priority=rule['priority'],
                nutrient_id=nutrient_id,
                threshold_amount=rule.get('threshold_amount'),
                threshold_unit=rule.get('threshold_unit'),
                is_conditional=rule.get('is_conditional', False),
                condition_parameter=rule.get('condition_parameter'),
                condition_operator=rule.get('condition_operator'),
                condition_value=rule.get('condition_value'),
                rationale=rule['rationale'],
                rule_status='ACTIVE'
            )
            db.add(cnr)


def seed_drug_nutrient_depletions(db):
    """Seed known drug-nutrient depletions. Idempotent."""
    from models.medication import Medication, DrugNutrientDepletion
    from models.food import Nutrient
    
    DEPLETIONS = [
        # (generic_name, nutrient, severity, mechanism, recommendation)
        ('metformin', 'vitamin_b12', 'significant',
         'Reduces ileal absorption of B12 via calcium-dependent mechanism',
         'Monitor B12 annually. Ensure dietary sources: curd, paneer, eggs if non-veg.'),
        
        ('atorvastatin', 'coq10', 'moderate',
         'Statins inhibit mevalonate pathway, reducing endogenous CoQ10 synthesis',
         'Include nuts, whole grains. Discuss CoQ10 monitoring if fatigue or myalgia occurs.'),
        
        ('rosuvastatin', 'coq10', 'moderate',
         'Same mechanism as atorvastatin',
         'Include nuts, whole grains. Discuss CoQ10 monitoring if fatigue or myalgia occurs.'),
        
        ('pantoprazole', 'vitamin_b12', 'moderate',
         'Reduces gastric acid needed for B12 release from food proteins',
         'Monitor B12 with long-term use. Include dairy or eggs if non-veg.'),
        
        ('pantoprazole', 'calcium', 'moderate',
         'Reduces calcium absorption by decreasing gastric acid',
         'Ensure adequate calcium intake: curd, ragi, sesame seeds.'),
        
        ('pantoprazole', 'magnesium', 'moderate',
         'Long-term PPI use associated with hypomagnesaemia',
         'Include nuts, seeds, whole grains.'),
        
        ('omeprazole', 'vitamin_b12', 'moderate',
         'Same mechanism as pantoprazole',
         'Monitor B12 with long-term use.'),
        
        ('omeprazole', 'calcium', 'moderate',
         'Same mechanism as pantoprazole',
         'Ensure adequate calcium intake.'),
        
        ('omeprazole', 'magnesium', 'moderate',
         'Same mechanism as pantoprazole',
         'Include nuts, seeds, whole grains.'),
        
        ('hydrochlorothiazide', 'potassium', 'significant',
         'Increases renal potassium excretion',
         'Include banana, curd, coconut water unless CKD Stage 4+ restricts potassium.'),
        
        ('hydrochlorothiazide', 'magnesium', 'moderate',
         'Increases renal magnesium excretion',
         'Include nuts, seeds, leafy greens.'),
        
        ('hydrochlorothiazide', 'zinc', 'minor',
         'Increases renal zinc excretion',
         'Include pumpkin seeds, sesame, whole dals.'),
        
        ('enalapril', 'zinc', 'minor',
         'ACE inhibitors may increase urinary zinc loss',
         'Include pumpkin seeds, sesame seeds, rajma.'),
        
        ('ramipril', 'zinc', 'minor',
         'Same mechanism as enalapril',
         'Include pumpkin seeds, sesame seeds, rajma.'),
    ]
    
    for generic_name, nutrient_name, severity, mechanism, recommendation in DEPLETIONS:
        med = db.query(Medication).filter(
            Medication.generic_name == generic_name
        ).first()
        if not med:
            print(f'  WARNING: medication not found for depletion: {generic_name}')
            continue
            
        nutr = db.query(Nutrient).filter(
            Nutrient.name.ilike(nutrient_name)
        ).first()
        if not nutr:
            # Create dummy nutrient just for testing
            nutr = Nutrient(name=nutrient_name, unit="mg", )
            db.add(nutr)
            db.commit()
            db.refresh(nutr)
        
        # Idempotent check
        existing = db.query(DrugNutrientDepletion).filter(
            DrugNutrientDepletion.medication_id == med.medication_id,
            DrugNutrientDepletion.nutrient_id == nutr.nutrient_id
        ).first()
        
        if not existing:
            depletion = DrugNutrientDepletion(
                medication_id=med.medication_id,
                nutrient_id=nutr.nutrient_id,
                severity=severity,
                mechanism=mechanism,
                recommendation=recommendation,
            )
            db.add(depletion)
            print(f'  Seeded: {generic_name} depletes {nutrient_name}')
    
    db.commit()
    print('DrugNutrientDepletion seeding complete.')

def run_seed():
    db = SessionLocal()
    try:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, 'seeds', 'foods_indian.json'), 'r') as f:
            foods_data = json.load(f)
        with open(os.path.join(base_dir, 'seeds', 'medications.json'), 'r') as f:
            meds_data = json.load(f)
        with open(os.path.join(base_dir, 'seeds', 'conditions.json'), 'r') as f:
            conds_data = json.load(f)
            
        seed_users(db)
        seed_foods(db, foods_data)
        seed_medications(db, meds_data)
        seed_conditions(db, conds_data)
        seed_drug_nutrient_depletions(db)
        
        db.commit()
        print("Seed completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Seed failed and rolled back: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
