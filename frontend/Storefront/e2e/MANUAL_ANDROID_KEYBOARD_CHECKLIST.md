# Manual Android Chrome keyboard checklist (#462)

**Purpose:** Physical keyboard / focus evidence complementing Playwright `KEYBOARD_LAYOUT_PROXY`.  
**Does not require payment** — stop before «پرداخت» / gateway if preferred.

Environment: Android phone, Chrome, staging storefront (`www.karzartools.com` or approved host), Owner-controlled test account.

| Step | Field / action | Pass criteria |
|------|----------------|---------------|
| 1 | Open login / checkout auth | Phone field focusable; keyboard opens |
| 2 | Phone (`inputmode=tel`) | Focus visible; value editable; CTA «دریافت کد» reachable (scroll if needed) |
| 3 | OTP (`inputmode=numeric`) | Focus visible; no bottom nav covers input; «تأیید و ادامه» reachable |
| 4 | Province | Persian «تهران» retained after blur |
| 5 | City | Persian «تهران» retained after blur |
| 6 | Postal code | Digits retained; label visible |
| 7 | Full address | Persian address retained; RTL readable |
| 8 | Full name | «کاربر آزمایشی» (or test name) retained |
| 9 | Keyboard open/close | Closing keyboard restores layout; no trapped focus |
| 10 | Checkout mobile dock | «پرداخت» not hidden behind bottom nav when last field focused |
| 11 | Bottom nav | «خانه» / «سبد» do not steal taps from form CTAs |
| 12 | Autofill (optional) | If system autofill appears, layout not broken; values still editable |

Record: device model, Android version, Chrome version, viewport-ish width, date, tester initials.  
Do **not** log OTP, card data, or full payment references.
