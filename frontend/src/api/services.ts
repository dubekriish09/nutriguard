import client from './client';
import { Token, ChatRequest, ChatResponse, UserContext, RecommendationResult } from '../types/api.types';

export const authApi = {
  login: async (formData: URLSearchParams): Promise<Token> => {
    const { data } = await client.post<Token>('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return data;
  }
};

export const chatApi = {
  foodChat: async (req: ChatRequest): Promise<ChatResponse> => {
    const { data } = await client.post<ChatResponse>('/api/v1/chat/food', req);
    return data;
  }
};

export const recommendationsApi = {
  evaluateFood: async (foodId: string, context: UserContext): Promise<RecommendationResult> => {
    const { data } = await client.post(`/api/v1/recommendations/evaluate/${foodId}`, context);
    return data;
  }
};
