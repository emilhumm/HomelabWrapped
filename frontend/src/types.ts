/** What `homelab_wrapped/coverage` returns; mirrors core/coverage.py. */

export type CardId =
  | "intro"
  | "uptime"
  | "restarts"
  | "blocked"
  | "media"
  | "power"
  | "personality"
  | "summary";

export type CardState = "ready" | "counting" | "locked";

export type Hint =
  | "history_break"
  | "price_hourly"
  | "price_live"
  | "price_fixed"
  | "price_missing"
  | "pick_meters";

export interface CardCoverage {
  card: CardId;
  number: number;
  state: CardState;
  /** ISO date: how far back the data goes, or since when it is collected. */
  since: string | null;
  /** ISO date a counting card will be ready. */
  ready_on: string | null;
  sources: string[];
  unlock: string[];
  hints: Hint[];
}

export interface Coverage {
  installed: string;
  cards: CardCoverage[];
  signals: Record<string, number>;
  /** Years with data, oldest first. */
  years: number[];
  /** The year to play first: the one that just ended, in January. */
  year: number;
}

/** The parts of Home Assistant's `hass` object the panel uses. */
export interface HomeAssistant {
  callWS<T>(message: { type: string; [key: string]: unknown }): Promise<T>;
  locale?: { language: string };
  language?: string;
}

/** What `homelab_wrapped/cards` returns; mirrors core/cards.py. */

export interface Streak {
  name: string;
  days: number;
  start: string;
  end: string;
  ongoing: boolean;
  /** Starts where the data starts: the real streak may be longer. */
  open_start: boolean;
}

interface CardBase {
  state: CardState;
  since: string | null;
}

export interface IntroCard extends CardBase {
  card: "intro";
  hosts: number;
  guests: number;
  containers: number;
  machines: number;
}

export interface UptimeCard extends CardBase {
  /** A past year: "up at the end of the year", not "up right now". Newer backends only. */
  over?: boolean;
  card: "uptime";
  /** Null in a lab whose only uptime data are monitored services. */
  longest: Streak | null;
  current: Streak[];
  machines: number;
  /** Restarts per day from `start`; null for days before any data. */
  grid: { start: string; restarts: (number | null)[] };
  /** Monitored services (Uptime Kuma): their average uptime over the past year. */
  services: Services | null;
}

export interface Services {
  count: number;
  /** Percent. */
  uptime: number;
  /** The least reliable, those under 100 %. */
  least: { name: string; uptime: number }[];
}

export interface RestartsCard extends CardBase {
  card: "restarts";
  total: number;
  machines: { name: string; restarts: number }[];
  never: string[];
  busiest_day: { date: string; restarts: number } | null;
  by_hour: number[];
  by_weekday: number[];
  /** Docker containers, ranked apart: one reboot of a Docker host restarts them all. */
  containers: RestartGroup | null;
  /** Routers, access points, the firewall: they serve the lab, ranked apart from its machines. */
  network?: RestartGroup | null;
}

/** Containers or network gear: a ranking of their own on the Restarts card. */
export interface RestartGroup {
  total: number;
  watched: number;
  top: { name: string; restarts: number }[];
  since: string | null;
}

export interface BlockedCard extends CardBase {
  card: "blocked";
  total: number;
  per_day: number;
  days: number;
  best_day: { date: string; blocked: number };
}

export interface MediaCard extends CardBase {
  card: "media";
  hours: number;
  /** Hours per month, January first; null outside the data. */
  by_month: (number | null)[];
  best_day: { date: string; hours: number };
  servers: { name: string; hours: number }[];
  /** Most played: the series of an episode, the artist of a song, else the title. */
  /** Newer backends only: optional, so a newer panel works before HA restarts. */
  titles?: { title: string; hours: number }[];
}

export interface PowerCard extends CardBase {
  card: "power";
  /** Null in a lab with a UPS but no meters picked: the card is its power cuts. */
  kwh: number | null;
  /** The lab's average draw. */
  watts: number | null;
  cost: number | null;
  currency: string | null;
  average_price: number | null;
  /** Some hours had no price and were priced at the average. */
  estimated: boolean;
  by_month: (number | null)[];
  meters: { name: string; kwh: number }[];
  /** Times the UPS switched to battery in the year; null without a UPS. */
  power_cuts: PowerCuts | null;
}

export interface PowerCuts {
  count: number;
  minutes: number;
  longest_minutes: number;
  /** Exact; newer backends only (minutes are rounded: a 20-second flicker is 0). */
  seconds?: number;
  longest_seconds?: number;
  since: string | null;
}

export interface Trait {
  key: string;
  /** The number behind it, e.g. days up or restarts at night (percent). */
  value: number;
  score: number;
}

export interface PersonalityCard extends CardBase {
  card: "personality";
  key: string;
  /** The strongest traits, strongest first. */
  traits: Trait[];
}

export type StoryCard =
  | PersonalityCard
  | IntroCard
  | UptimeCard
  | RestartsCard
  | BlockedCard
  | MediaCard
  | PowerCard;

export interface CardsResponse {
  year: number;
  cards: StoryCard[];
}
