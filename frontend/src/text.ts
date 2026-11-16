/**
 * Every text the panel shows, in English and Danish. ``useLanguage`` picks the
 * set for Home Assistant's language once the panel knows it; English otherwise.
 * The exports are live bindings, so every module sees the language picked.
 */

import type { CardId, Hint } from "./types";

/** End with one full stop, also after an amount that has its own ("963 kr."). */
const sentence = (text: string): string => (text.endsWith(".") ? text : `${text}.`);

export interface Personality {
  name: string;
  tagline: string;
  /** A Material Design Icon, drawn by Home Assistant's own ha-icon (emoji vary by device). */
  icon: string;
  /** Why this trait shows, from its number (already formatted) and the year played. */
  reason: (value: string, year: number) => string;
}

const CARDS_EN: Record<CardId, { title: string; about: string }> = {
  intro: { title: "Your lab", about: "Hosts, guests and containers" },
  uptime: { title: "Uptime", about: "The longest streak without a restart" },
  restarts: { title: "Restarts", about: "What restarted most" },
  blocked: { title: "Blocked", about: "DNS queries your blocker stopped" },
  media: { title: "Media", about: "Hours streamed from your media server" },
  power: { title: "Power", about: "What the lab used, and what it cost" },
  personality: { title: "Personality", about: "Your homelab personality" },
  summary: { title: "Summary", about: "One image to share" },
};

const HINTS_EN: Record<Hint, string> = {
  history_break:
    "An integration update stopped a sensor's history; Wrapped stitches the old history to what it records now.",
  price_hourly: "Priced hour by hour with your price sensor.",
  price_live: "Your price sensor has no history yet; prices are collected from now on.",
  price_fixed: "Priced with the fixed price from your Energy dashboard.",
  price_missing: "Add a price to the Energy dashboard to see what it cost.",
  pick_meters:
    "Pick the energy meters your lab is on (smart plugs, a PDU, a UPS that measures kWh) in Homelab Wrapped's options: Settings → Devices & services → Homelab Wrapped → Configure.",
};

const TEXT_EN = {
  title: "Homelab Wrapped",
  heading: "Your lab can make these cards today",
  readyCount: (ready: number, total: number) => `${ready} of ${total} ready`,
  ready: "Ready",
  counting: "Counting",
  locked: "Locked",
  since: (date: string) => `Since ${date}`,
  readyOn: (date: string) => `Ready ${date}`,
  collectingSince: (date: string) => `Collecting since ${date}`,
  from: (names: string) => `From ${names}`,
  connect: (names: string) => `Connect ${names}`,
  builtFromOthers: "Built from the other cards",
  copy: "Copy diagnostics",
  copied: "Copied: no names, hostnames or IPs",
  copyFailed: "Couldn't copy; your browser blocked it",
  privacy: "Read-only. Nothing leaves your network.",
  refresh: "Check again",
  loading: "Checking what your lab has…",
  failed: (message: string) => `Couldn't check your lab: ${message}`,
  storyFailed: (message: string) => `Couldn't load your Wrapped: ${message}`,
};

const STORY_EN = {
  play: (year: number) => `Play your ${year} Wrapped`,
  years: "Which year",
  loadingCards: "Wrapping up your year…",
  noCards: "No cards yet: connect something above, or give Wrapped a week.",
  close: "Close",
  previous: "Previous card",
  next: "Next card",
  earlyLook: "Early look: Wrapped is still counting",
  sinceNote: (date: string) => `Since ${date}`,

  introKicker: (year: number) => `Your ${year} in the lab`,
  introTitle: "Here's what kept your homelab busy.",
  hosts: (n: number): string => (n === 1 ? "host" : "hosts"),
  guests: (n: number): string => (n === 1 ? "guest" : "guests"),
  containers: (n: number): string => (n === 1 ? "container" : "containers"),
  watching: (n: string) => `Wrapped watched ${n} ${n === "1" ? "machine" : "machines"}.`,

  uptimeKicker: "Longest streak",
  days: (n: string) => `${n} ${n === "1" ? "day" : "days"}`,
  uptimeLine: (name: string, ongoing: boolean, open: boolean, over: boolean) =>
    `${open ? "At least that long: " : ""}${name} went without a single restart${
      ongoing ? (over ? ", and was still going at the end of the year" : ", and it's still going") : ""
    }.`,
  currentStreaks: "Up right now",
  upAtYearEnd: "Up at the end of the year",
  servicesKicker: "Services",
  servicesUp: (n: number, percent: string) =>
    `${n === 1 ? "Your monitored service was" : `Your ${n} monitored services were`} up ${percent} of the past year.`,
  leastReliable: "Least reliable",
  summaryServices: (_n: string): string => "services up",
  gridTitle: "Your year, day by day",
  gridUp: "Up all day",
  gridRestart: "Restarted 1, 2, 3+ times",
  gridUnknown: "No data",

  restartsKicker: "Restarts",
  restartsMost: (name: string, n: string) => `${name} restarted most: ${n} ${n === "1" ? "time" : "times"}.`,
  restartsNone: "Not a single restart. Impressive.",
  busiestDay: (date: string, n: string) => `Busiest day: ${date}, with ${n} restarts.`,
  favouriteHour: (hour: string) => `Restarts like to happen around ${hour}.`,
  never: (names: string) => `Never restarted: ${names}.`,
  andMore: (names: string, n: number) => `${names} and ${n} more`,
  containersKicker: "Container restarts",
  containersMost: (total: string, name: string, n: string) =>
    `Your containers restarted ${total} ${total === "1" ? "time" : "times"}. ${name} led with ${n}.`,
  containersNone: (n: string) =>
    n === "1" ? "Your container didn't restart." : `None of your ${n} containers restarted.`,
  networkKicker: "Network restarts",
  networkMost: (total: string, name: string, n: string) =>
    `Your network gear restarted ${total} ${total === "1" ? "time" : "times"}. ${name} led with ${n}.`,
  networkNone: (n: string) =>
    n === "1" ? "Your network device didn't restart." : `None of your ${n} network devices restarted.`,
  machinesTitle: "Machines",
  containersTitle: "Containers",
  networkTitle: "Network",

  blockedKicker: "Blocked",
  blockedTitle: (n: string) => `${n} DNS ${n === "1" ? "query" : "queries"} blocked`,
  perDay: (n: string) => `That's ${n} a day kept away from your devices.`,
  bestBlockedDay: (date: string, n: string) => `Busiest day: ${date}, with ${n} blocked.`,

  mediaKicker: "Media",
  mediaTitle: (n: string) => `${n === "1" ? "hour" : "hours"} of films, shows and music played.`,
  mediaDays: (n: string) => `That's ${n} days of non-stop streaming.`,
  bestMediaDay: (date: string, n: string) => `Biggest day: ${date}, with ${n} ${n === "1" ? "hour" : "hours"}.`,
  topTitle: (title: string, n: string) => `Played most: ${title}, ${n} ${n === "1" ? "hour" : "hours"}.`,
  topTitles: "Most played",
  hoursUnit: "h",
  servers: "Per media server",

  powerKicker: "Power",
  powerTitle: "kWh to keep the lab running.",
  powerCost: (cost: string, estimated: boolean) => sentence(`That cost ${estimated ? "about " : ""}${cost}`),
  powerWatts: (watts: string) => `An average of ${watts} W, day and night.`,
  powerPrice: (price: string) => `You paid ${price} per kWh on average.`,
  cutsKicker: "Power cuts",
  cutsTitle: (n: number): string => (n === 1 ? "power cut your UPS rode out." : "power cuts your UPS rode out."),
  /** ``total`` and ``longest`` are durations: STORY.seconds/minutes/hours. */
  cuts: (n: string, total: string, longest: string) =>
    n === "1"
      ? `Your UPS rode out one power cut: ${total} on battery.`
      : `Your UPS rode out ${n} power cuts: ${total} on battery, the longest ${longest}.`,
  seconds: (n: string) => `${n} ${n === "1" ? "second" : "seconds"}`,
  minutes: (n: string) => `${n} ${n === "1" ? "minute" : "minutes"}`,
  hours: (n: string) => `${n} ${n === "1" ? "hour" : "hours"}`,
  noCuts: "Not one power cut: your UPS never had to step in.",
  summaryCuts: (n: string): string => (n === "1" ? "power cut" : "power cuts"),

  summaryKicker: (year: number) => `That was ${year}`,
  summaryTitle: "Your homelab, wrapped.",
  summaryStreak: (n: string): string => (n === "1" ? "day without a restart" : "days without a restart"),
  summaryRestarts: (n: string): string => (n === "1" ? "restart" : "restarts"),
  summaryContainerRestarts: (n: string): string => (n === "1" ? "container restart" : "container restarts"),
  summaryNetworkRestarts: (n: string): string => (n === "1" ? "network restart" : "network restarts"),
  summaryBlocked: (n: string): string => (n === "1" ? "query blocked" : "queries blocked"),
  summaryMedia: (n: string): string => (n === "1" ? "hour played" : "hours played"),
  summaryPower: (_n: string): string => "kWh used",
  personalityKicker: "Your homelab personality",
  personalityWhy: "Why",
  summaryMachines: (n: string): string => (n === "1" ? "machine watched" : "machines watched"),
  done: "Done",
};

const PERSONALITIES_EN: Record<string, Personality> = {
  rock: {
    name: "The Rock",
    tagline: "Set it and forget it. Your lab just keeps going.",
    icon: "mdi:image-filter-hdr",
    reason: (value) => `${value} ${value === "1" ? "day" : "days"} without a single restart`,
  },
  tinkerer: {
    name: "The Tinkerer",
    tagline: "Something is always being upgraded, rebuilt or tried out.",
    icon: "mdi:wrench",
    reason: (value, year) => `${value} ${value === "1" ? "restart" : "restarts"} in ${year}`,
  },
  night_owl: {
    name: "The Night Owl",
    tagline: "Your maintenance window starts after bedtime.",
    icon: "mdi:owl",
    reason: (value) => `${value}% of restarts between 22:00 and 05:00`,
  },
  weekend_warrior: {
    name: "The Weekend Warrior",
    tagline: "Saturdays are for upgrades.",
    icon: "mdi:hammer-wrench",
    reason: (value) => `${value}% of restarts on a weekend`,
  },
  gatekeeper: {
    name: "The Gatekeeper",
    tagline: "Nothing gets past your DNS.",
    icon: "mdi:shield-check",
    reason: (value) => `${value} ${value === "1" ? "query" : "queries"} blocked a day`,
  },
  cinephile: {
    name: "The Cinephile",
    tagline: "Your media server is the busiest machine in the house.",
    icon: "mdi:popcorn",
    reason: (value) => `${value} ${value === "1" ? "hour" : "hours"} played a day`,
  },
  sipper: {
    name: "The Sipper",
    tagline: "The whole lab draws less than an old light bulb.",
    icon: "mdi:leaf",
    reason: (value) => `${value} W on average`,
  },
  survivor: {
    name: "The Survivor",
    tagline: "The power goes out. Your lab doesn't.",
    icon: "mdi:home-battery",
    reason: (value) => `${value} ${value === "1" ? "power cut" : "power cuts"} ridden out`,
  },
  power_plant: {
    name: "The Power Plant",
    tagline: "Your lab could heat a small room. It probably does.",
    icon: "mdi:lightning-bolt",
    reason: (value) => `${value} W on average`,
  },
  collector: {
    name: "The Collector",
    tagline: "Why run one service when you can run them all?",
    icon: "mdi:package-variant-closed",
    reason: (value) => `${value} ${value === "1" ? "guest or container" : "guests and containers"}`,
  },
  all_rounder: {
    name: "The All-Rounder",
    tagline: "A bit of everything, nothing overdone.",
    icon: "mdi:compass-outline",
    reason: () => "",
  },
};

const SHARE_EN = {
  brand: "Homelab Wrapped",
  footer: "Made with Homelab Wrapped for Home Assistant",
  /** ``days`` is STORY.days(...): "1 day", "107 days". */
  longestBy: (name: string, days: string) => `Longest streak: ${name}, ${days}`,
  button: "Share image",
  title: "Your share image",
  names: "Show machine names",
  namesHint: "Off by default: hostnames can tell more about your network than you'd like to share.",
  save: "Save image",
  back: "Back",
  failed: "Couldn't save the image.",
};

const CARDS_DA: typeof CARDS_EN = {
  intro: { title: "Dit lab", about: "Værter, gæster og containere" },
  uptime: { title: "Oppetid", about: "Den længste stime uden en genstart" },
  restarts: { title: "Genstarter", about: "Hvad der genstartede mest" },
  blocked: { title: "Blokeret", about: "DNS-forespørgsler, som din DNS-blokker stoppede" },
  media: { title: "Medier", about: "Timer streamet fra din medieserver" },
  power: { title: "Strøm", about: "Hvad labbet brugte, og hvad det kostede" },
  personality: { title: "Personlighed", about: "Dit homelabs personlighed" },
  summary: { title: "Opsummering", about: "Ét billede at dele" },
};

const HINTS_DA: typeof HINTS_EN = {
  history_break:
    "En opdatering af en integration stoppede en sensors historik; Wrapped syr den gamle historik sammen med det, den registrerer nu.",
  price_hourly: "Prissat time for time med din prissensor.",
  price_live: "Din prissensor har ingen historik endnu; priserne samles fra nu af.",
  price_fixed: "Prissat med den faste pris fra dit Energi-dashboard.",
  price_missing: "Tilføj en pris i Energi-dashboardet for at se, hvad det kostede.",
  pick_meters:
    "Vælg de energimålere, dit lab sidder på (smartstik, en PDU, en UPS, der måler kWh), i Homelab Wrappeds indstillinger: Indstillinger → Enheder og tjenester → Homelab Wrapped → Konfigurer.",
};

const TEXT_DA: typeof TEXT_EN = {
  title: "Homelab Wrapped",
  heading: "Dit lab kan lave disse kort i dag",
  readyCount: (ready, total) => `${ready} af ${total} klar`,
  ready: "Klar",
  counting: "Tæller",
  locked: "Låst",
  since: (date) => `Siden ${date}`,
  readyOn: (date) => `Klar ${date}`,
  collectingSince: (date) => `Samler data siden ${date}`,
  from: (names) => `Fra ${names}`,
  connect: (names) => `Forbind ${names}`,
  builtFromOthers: "Bygget ud fra de andre kort",
  copy: "Kopiér diagnostik",
  copied: "Kopieret: ingen navne, værtsnavne eller IP-adresser",
  copyFailed: "Kunne ikke kopiere; din browser blokerede det",
  privacy: "Læser kun. Intet forlader dit netværk.",
  refresh: "Tjek igen",
  loading: "Tjekker, hvad dit lab har…",
  failed: (message) => `Kunne ikke tjekke dit lab: ${message}`,
  storyFailed: (message) => `Kunne ikke hente dit Wrapped: ${message}`,
};

const STORY_DA: typeof STORY_EN = {
  play: (year) => `Se dit Wrapped for ${year}`,
  years: "Hvilket år",
  loadingCards: "Pakker dit år ind…",
  noCards: "Ingen kort endnu: forbind noget ovenfor, eller giv Wrapped en uge.",
  close: "Luk",
  previous: "Forrige kort",
  next: "Næste kort",
  earlyLook: "Et tidligt kig: Wrapped tæller stadig",
  sinceNote: (date) => `Siden ${date}`,

  introKicker: (year) => `Dit ${year} i labbet`,
  introTitle: "Her er, hvad der gav dit homelab travlt.",
  hosts: (n) => (n === 1 ? "vært" : "værter"),
  guests: (n) => (n === 1 ? "gæst" : "gæster"),
  containers: (n) => (n === 1 ? "container" : "containere"),
  watching: (n) => `Wrapped holdt øje med ${n} ${n === "1" ? "maskine" : "maskiner"}.`,

  uptimeKicker: "Længste stime",
  days: (n) => `${n} ${n === "1" ? "dag" : "dage"}`,
  uptimeLine: (name, ongoing, open, over) =>
    `${open ? "Mindst så længe: " : ""}${name} kørte uden en eneste genstart${
      ongoing ? (over ? ", og den kørte stadig ved årets udgang" : ", og den kører stadig") : ""
    }.`,
  currentStreaks: "Kører lige nu",
  upAtYearEnd: "Kørte ved årets udgang",
  servicesKicker: "Tjenester",
  servicesUp: (n, percent) =>
    `${n === 1 ? "Din overvågede tjeneste" : `Dine ${n} overvågede tjenester`} var oppe ${percent} af det seneste år.`,
  leastReliable: "Mindst pålidelige",
  summaryServices: () => "tjenester oppe",
  gridTitle: "Dit år, dag for dag",
  gridUp: "Oppe hele dagen",
  gridRestart: "Genstartet 1, 2, 3+ gange",
  gridUnknown: "Ingen data",

  restartsKicker: "Genstarter",
  restartsMost: (name, n) => `${name} genstartede mest: ${n} ${n === "1" ? "gang" : "gange"}.`,
  restartsNone: "Ikke en eneste genstart. Imponerende.",
  busiestDay: (date, n) => `Travleste dag: ${date}, med ${n} genstarter.`,
  favouriteHour: (hour) => `Genstarter sker gerne omkring kl. ${hour}.`,
  never: (names) => `Aldrig genstartet: ${names}.`,
  andMore: (names, n) => `${names} og ${n} mere`,
  containersKicker: "Containergenstarter",
  containersMost: (total, name, n) =>
    `Dine containere genstartede ${total} ${total === "1" ? "gang" : "gange"}. ${name} førte an med ${n}.`,
  containersNone: (n) => (n === "1" ? "Din container genstartede ikke." : `Ingen af dine ${n} containere genstartede.`),
  networkKicker: "Netværksgenstarter",
  networkMost: (total, name, n) =>
    `Dit netværksudstyr genstartede ${total} ${total === "1" ? "gang" : "gange"}. ${name} førte an med ${n}.`,
  networkNone: (n) =>
    n === "1" ? "Din netværksenhed genstartede ikke." : `Ingen af dine ${n} netværksenheder genstartede.`,
  machinesTitle: "Maskiner",
  containersTitle: "Containere",
  networkTitle: "Netværk",

  blockedKicker: "Blokeret",
  blockedTitle: (n) => `${n} DNS-${n === "1" ? "forespørgsel" : "forespørgsler"} blokeret`,
  perDay: (n) => `Det er ${n} om dagen, der aldrig nåede dine enheder.`,
  bestBlockedDay: (date, n) => `Travleste dag: ${date}, med ${n} blokerede.`,

  mediaKicker: "Medier",
  mediaTitle: (n) => `${n === "1" ? "time" : "timer"} med film, serier og musik.`,
  mediaDays: (n) => `Det svarer til ${n} døgn med streaming i ét stræk.`,
  bestMediaDay: (date, n) => `Travleste dag: ${date}, med ${n} ${n === "1" ? "time" : "timer"}.`,
  topTitle: (title, n) => `Mest afspillet: ${title}, ${n} ${n === "1" ? "time" : "timer"}.`,
  topTitles: "Mest afspillet",
  hoursUnit: "t",
  servers: "Pr. medieserver",

  powerKicker: "Strøm",
  powerTitle: "kWh for at holde labbet kørende.",
  powerCost: (cost, estimated) => sentence(`Det kostede ${estimated ? "omkring " : ""}${cost}`),
  powerWatts: (watts) => `I gennemsnit ${watts} W, døgnet rundt.`,
  powerPrice: (price) => `Du betalte i gennemsnit ${price} pr. kWh.`,
  cutsKicker: "Strømafbrydelser",
  cutsTitle: (n) => (n === 1 ? "strømafbrydelse klaret af din UPS." : "strømafbrydelser klaret af din UPS."),
  cuts: (n, total, longest) =>
    n === "1"
      ? `Din UPS klarede én strømafbrydelse: ${total} på batteri.`
      : `Din UPS klarede ${n} strømafbrydelser: ${total} på batteri, den længste ${longest}.`,
  seconds: (n) => `${n} ${n === "1" ? "sekund" : "sekunder"}`,
  minutes: (n) => `${n} ${n === "1" ? "minut" : "minutter"}`,
  hours: (n) => `${n} ${n === "1" ? "time" : "timer"}`,
  noCuts: "Ikke én strømafbrydelse: din UPS behøvede aldrig at træde til.",
  summaryCuts: (n) => (n === "1" ? "strømafbrydelse" : "strømafbrydelser"),

  summaryKicker: (year) => `Det var ${year}`,
  summaryTitle: "Dit homelab, pakket ind.",
  summaryStreak: (n) => (n === "1" ? "dag uden genstart" : "dage uden genstart"),
  summaryRestarts: (n) => (n === "1" ? "genstart" : "genstarter"),
  summaryContainerRestarts: (n) => (n === "1" ? "containergenstart" : "containergenstarter"),
  summaryNetworkRestarts: (n) => (n === "1" ? "netværksgenstart" : "netværksgenstarter"),
  summaryBlocked: (n) => (n === "1" ? "forespørgsel blokeret" : "forespørgsler blokeret"),
  summaryMedia: (n) => (n === "1" ? "time afspillet" : "timer afspillet"),
  summaryPower: () => "kWh brugt",
  personalityKicker: "Dit homelabs personlighed",
  personalityWhy: "Hvorfor",
  summaryMachines: (n) => (n === "1" ? "maskine overvåget" : "maskiner overvåget"),
  done: "Færdig",
};

const PERSONALITIES_DA: typeof PERSONALITIES_EN = {
  rock: {
    name: "Klippen",
    tagline: "Sæt det op og glem det. Dit lab bliver bare ved.",
    icon: "mdi:image-filter-hdr",
    reason: (value) => `${value} ${value === "1" ? "dag" : "dage"} uden en eneste genstart`,
  },
  tinkerer: {
    name: "Nørkleren",
    tagline: "Der bliver altid opgraderet, bygget om eller prøvet noget nyt.",
    icon: "mdi:wrench",
    reason: (value, year) => `${value} ${value === "1" ? "genstart" : "genstarter"} i ${year}`,
  },
  night_owl: {
    name: "Natteravnen",
    tagline: "Dit servicevindue starter efter sengetid.",
    icon: "mdi:owl",
    reason: (value) => `${value} % af genstarterne mellem kl. 22 og 05`,
  },
  weekend_warrior: {
    name: "Weekendkrigeren",
    tagline: "Lørdage er til opgraderinger.",
    icon: "mdi:hammer-wrench",
    reason: (value) => `${value} % af genstarterne i weekenden`,
  },
  gatekeeper: {
    name: "Dørmanden",
    tagline: "Intet slipper forbi din DNS.",
    icon: "mdi:shield-check",
    reason: (value) => `${value} ${value === "1" ? "forespørgsel" : "forespørgsler"} blokeret om dagen`,
  },
  cinephile: {
    name: "Filmnørden",
    tagline: "Din medieserver er husets travleste maskine.",
    icon: "mdi:popcorn",
    reason: (value) => `${value} ${value === "1" ? "time" : "timer"} afspillet om dagen`,
  },
  sipper: {
    name: "Sparegrisen",
    tagline: "Hele labbet bruger mindre end en gammel glødepære.",
    icon: "mdi:leaf",
    reason: (value) => `${value} W i gennemsnit`,
  },
  survivor: {
    name: "Overleveren",
    tagline: "Strømmen går. Det gør dit lab ikke.",
    icon: "mdi:home-battery",
    reason: (value) => `${value} ${value === "1" ? "strømafbrydelse" : "strømafbrydelser"} klaret`,
  },
  power_plant: {
    name: "Kraftværket",
    tagline: "Dit lab kunne varme et lille værelse op. Det gør det nok.",
    icon: "mdi:lightning-bolt",
    reason: (value) => `${value} W i gennemsnit`,
  },
  collector: {
    name: "Samleren",
    tagline: "Hvorfor køre én tjeneste, når du kan køre dem alle?",
    icon: "mdi:package-variant-closed",
    reason: (value) => `${value} ${value === "1" ? "gæst eller container" : "gæster og containere"}`,
  },
  all_rounder: {
    name: "Den alsidige",
    tagline: "Lidt af det hele, intet overdrevet.",
    icon: "mdi:compass-outline",
    reason: () => "",
  },
};

const SHARE_DA: typeof SHARE_EN = {
  brand: "Homelab Wrapped",
  footer: "Lavet med Homelab Wrapped til Home Assistant",
  longestBy: (name, days) => `Længste stime: ${name}, ${days}`,
  button: "Del billede",
  title: "Dit delebillede",
  names: "Vis maskinnavne",
  namesHint: "Slået fra som standard: værtsnavne kan sige mere om dit netværk, end du har lyst til at dele.",
  save: "Gem billede",
  back: "Tilbage",
  failed: "Kunne ikke gemme billedet.",
};

const LANGUAGES = {
  en: {
    cards: CARDS_EN,
    hints: HINTS_EN,
    text: TEXT_EN,
    story: STORY_EN,
    personalities: PERSONALITIES_EN,
    share: SHARE_EN,
  },
  da: {
    cards: CARDS_DA,
    hints: HINTS_DA,
    text: TEXT_DA,
    story: STORY_DA,
    personalities: PERSONALITIES_DA,
    share: SHARE_DA,
  },
};

export let CARDS = CARDS_EN;
export let HINTS = HINTS_EN;
export let TEXT = TEXT_EN;
export let STORY = STORY_EN;
export let PERSONALITIES = PERSONALITIES_EN;
export let SHARE = SHARE_EN;

/** Show the texts in ``language`` (such as "da" or "en-GB"); English for one there isn't. */
export function useLanguage(language: string | undefined): void {
  const code = (language ?? "").toLowerCase().split("-")[0];
  const texts = code === "da" ? LANGUAGES.da : LANGUAGES.en;
  CARDS = texts.cards;
  HINTS = texts.hints;
  TEXT = texts.text;
  STORY = texts.story;
  PERSONALITIES = texts.personalities;
  SHARE = texts.share;
}
