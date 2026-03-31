import { api } from "./api";

export interface WaitlistSignupPayload {
  email: string;
  source_page: string;
  source_label?: string;
  metadata?: Record<string, unknown>;
}

export interface WaitlistSignupResponse {
  status: "created" | "duplicate";
  message: string;
  storage: string;
}

export function submitWaitlistSignup(payload: WaitlistSignupPayload) {
  return api
    .post<WaitlistSignupResponse>("/waitlist", payload)
    .then((response) => response.data);
}
