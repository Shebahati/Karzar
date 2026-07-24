/** Zod schema for step-up PIN validation (C10). */

import { z } from "zod";
import { PIN_SCHEMA_MAX, PIN_SCHEMA_MIN } from "@/lib/constants";

export const stepUpPinSchema = z
  .string()
  .trim()
  .min(PIN_SCHEMA_MIN, { message: `کد امنیتی باید حداقل ${PIN_SCHEMA_MIN} رقم باشد.` })
  .max(PIN_SCHEMA_MAX, { message: `کد امنیتی نباید بیش از ${PIN_SCHEMA_MAX} رقم باشد.` });
