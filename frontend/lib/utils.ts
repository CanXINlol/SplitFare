export function money(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-AU", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

export function duration(minutes: number | null): string {
  if (minutes === null) return "Direct";
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return remaining ? `${hours}h ${remaining}m` : `${hours}h`;
}

export function clock(value: string): string {
  const localClock = value.match(/T(\d{2}):(\d{2})/);
  return localClock ? `${localClock[1]}:${localClock[2]}` : "Time unavailable";
}
