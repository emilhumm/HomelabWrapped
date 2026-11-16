/** Numbers, dates and hours in the user's language. */

export class Format {
  constructor(private readonly language: string) {}

  number(value: number, digits = 0): string {
    return new Intl.NumberFormat(this.language, { maximumFractionDigits: digits }).format(value);
  }

  /** Hours or kWh: one decimal under 10, so a first evening's 0.2 hours doesn't read as 0. */
  amount(value: number): string {
    return this.number(value, value < 10 ? 1 : 0);
  }

  /** "1,234 DKK" in the user's language; plain number and code for unknown currencies. */
  money(value: number, currency: string, digits = 0): string {
    try {
      return new Intl.NumberFormat(this.language, {
        style: "currency",
        currency,
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(value);
    } catch {
      return `${this.number(value, digits)} ${currency}`;
    }
  }

  /** "99.7%" or "99,7 %", from a value in percent. */
  percent(value: number, digits = 0): string {
    return new Intl.NumberFormat(this.language, { style: "percent", maximumFractionDigits: digits }).format(
      value / 100,
    );
  }

  /** 1,234 but 1.2M: big counts read better short. */
  big(value: number): string {
    if (value < 1_000_000) return this.number(value);
    return new Intl.NumberFormat(this.language, {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }

  /** "13 May" from an ISO date or date-time. */
  date(iso: string): string {
    const moment = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
    return moment.toLocaleDateString(this.language, { day: "numeric", month: "long" });
  }

  /** "3:00 AM" or "03:00" for an hour of the day. */
  hour(hour: number): string {
    return new Date(2000, 0, 1, hour).toLocaleTimeString(this.language, {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  /** "Jan" for month 0. */
  month(month: number): string {
    return new Date(2000, month, 1).toLocaleDateString(this.language, { month: "short" });
  }

  /** "Mon" for weekday 0 (Monday first, as the year grid). */
  weekday(day: number): string {
    return new Date(2024, 0, 1 + day).toLocaleDateString(this.language, { weekday: "short" });
  }
}
