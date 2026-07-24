"use client";

import { useMutation } from "@tanstack/react-query";

import { authService, type LoginPayload } from "@/services/auth";
import type { ApiError } from "@/lib/api-client";
import type { Token } from "@/types/auth";

export function useLogin() {
  return useMutation<Token, ApiError, LoginPayload>({
    mutationFn: (payload) => authService.login(payload),
  });
}
