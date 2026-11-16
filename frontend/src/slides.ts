/** One story slide per card, plus the closing summary. */

import { html, nothing, type TemplateResult } from "lit";

import type { Format } from "./format";
import { PERSONALITIES, STORY } from "./text";
import type {
  BlockedCard,
  RestartGroup,
  IntroCard,
  MediaCard,
  PersonalityCard,
  PowerCard,
  RestartsCard,
  StoryCard,
  UptimeCard,
} from "./types";

export function renderSlide(card: StoryCard, year: number, f: Format): TemplateResult {
  switch (card.card) {
    case "intro":
      return intro(card, year, f);
    case "uptime":
      return uptime(card, f);
    case "restarts":
      return restarts(card, f);
    case "blocked":
      return blocked(card, f);
    case "media":
      return media(card, f);
    case "power":
      return power(card, f);
    case "personality":
      return personality(card, year, f);
  }
}

function slide(
  card: StoryCard | null,
  kind: string,
  text: TemplateResult,
  visual: TemplateResult | typeof nothing,
  f: Format,
): TemplateResult {
  return html`
    <section class="slide ${kind}">
      <div class="text">
        ${text}
        <p class="note">
          ${card?.since ? STORY.sinceNote(f.date(card.since)) : nothing}
          ${card?.state === "counting" ? html`<span class="early">${STORY.earlyLook}</span>` : nothing}
        </p>
      </div>
      <div class="visual">${visual}</div>
    </section>
  `;
}

function intro(card: IntroCard, year: number, f: Format): TemplateResult {
  const tiles: [number, string][] = [
    [card.hosts, STORY.hosts(card.hosts)],
    [card.guests, STORY.guests(card.guests)],
    [card.containers, STORY.containers(card.containers)],
  ];
  return slide(
    card,
    "intro",
    html`
      <p class="kicker">${STORY.introKicker(year)}</p>
      <h2 class="title">${STORY.introTitle}</h2>
      ${card.machines ? html`<p class="line">${STORY.watching(f.number(card.machines))}</p>` : nothing}
    `,
    html`<div class="tiles">
      ${tiles.map(([count, label]) => html`<div class="tile"><b>${f.number(count)}</b><span>${label}</span></div>`)}
    </div>`,
    f,
  );
}

function uptime(card: UptimeCard, f: Format): TemplateResult {
  const best = card.longest;
  const services = card.services;
  if (!best) return servicesOnly(card, services, f);
  return slide(
    card,
    "uptime",
    html`
      <p class="kicker">${STORY.uptimeKicker}</p>
      <h2 class="hero">${STORY.days(f.number(best.days, best.days < 10 ? 1 : 0))}</h2>
      <p class="line">${STORY.uptimeLine(best.name, best.ongoing, best.open_start, card.over ?? false)}</p>
      ${services ? html`<p class="fact">${STORY.servicesUp(services.count, percent(services.uptime, f))}</p>` : nothing}
      ${card.current.length
        ? html`<p class="sub">${card.over ? STORY.upAtYearEnd : STORY.currentStreaks}</p>
            <ul class="list">
              ${card.current.slice(0, 3).map(
                (streak) => html`<li><span>${streak.name}</span><b>${STORY.days(f.amount(streak.days))}</b></li>`,
              )}
            </ul>`
        : nothing}
    `,
    yearGrid(card, f),
    f,
  );
}

/** A lab whose only uptime data are monitored services: the slide is about them. */
function servicesOnly(card: UptimeCard, services: UptimeCard["services"], f: Format): TemplateResult {
  if (!services) return html``;
  return slide(
    card,
    "uptime",
    html`
      <p class="kicker">${STORY.servicesKicker}</p>
      <h2 class="hero">${percent(services.uptime, f)}</h2>
      <p class="line">${STORY.servicesUp(services.count, percent(services.uptime, f))}</p>
    `,
    services.least.length
      ? html`<div>
          <p class="sub">${STORY.leastReliable}</p>
          <ul class="list">
            ${services.least.map((item) => html`<li><span>${item.name}</span><b>${percent(item.uptime, f)}</b></li>`)}
          </ul>
        </div>`
      : html`<div class="icon" aria-hidden="true"><ha-icon .icon=${"mdi:check-network"}></ha-icon></div>`,
    f,
  );
}

/** A percentage with as many decimals as it takes to tell 99.9 from 99.99, and 98.7 from 99. */
function percent(value: number, f: Format): string {
  if (value >= 100) return f.percent(100, 0);
  const digits = value >= 99.95 ? 2 : 1;
  // Down, never up: a service that was down at all wasn't up 100 %.
  const scale = 10 ** digits;
  return f.percent(Math.floor(value * scale) / scale, digits);
}

/** At most this many names in a list on a slide; the rest as "and 3 more". */
const TOP = 5;

function someOf(names: string[]): string {
  const shown = names.slice(0, TOP).join(", ");
  return names.length > TOP ? STORY.andMore(shown, names.length - TOP) : shown;
}

/** A number and its label, which can depend on it ("1 restart", "2 restarts"). */
export function stat(value: string, label: (n: string) => string): [string, string] {
  return [value, label(value)];
}

/** The summary's uptime number: the longest streak, or the services' uptime. */
export function uptimeStat(card: UptimeCard, f: Format): [string, string] {
  return card.longest
    ? stat(f.amount(card.longest.days), STORY.summaryStreak)
    : stat(percent(card.services?.uptime ?? 0, f), STORY.summaryServices);
}

function yearGrid(card: UptimeCard, f: Format): TemplateResult {
  const start = new Date(`${card.grid.start}T00:00:00`);
  const offset = (start.getDay() + 6) % 7; // Monday first
  const cells = [...Array<null>(offset).fill(null).map(() => "pad"), ...card.grid.restarts.map(cellClass)];
  return html`
    <figure class="year">
      <figcaption>${STORY.gridTitle}</figcaption>
      <div class="grid" role="img" aria-label=${STORY.gridTitle}>
        ${cells.map((cell) => html`<i class=${cell}></i>`)}
      </div>
      <div class="legend">
        <span><i class="up"></i>${STORY.gridUp}</span>
        <span><b class="scale"><i class="r1"></i><i class="r2"></i><i class="r3"></i></b>${STORY.gridRestart}</span>
        <span><i class="none"></i>${STORY.gridUnknown}</span>
        <span class="weekdays">${f.weekday(0)}–${f.weekday(6)} ↓</span>
      </div>
    </figure>
  `;
}

function cellClass(restarts: number | null): string {
  if (restarts === null) return "none";
  if (restarts === 0) return "up";
  return restarts === 1 ? "r1" : restarts === 2 ? "r2" : "r3";
}

function restarts(card: RestartsCard, f: Format): TemplateResult {
  const containers = card.containers;
  const network = card.network ?? null;
  const groupOnly = containers ?? network;
  if (!card.machines.length && groupOnly) return groupsOnly(card, groupOnly, f);
  const top = card.machines[0];
  const peak = card.by_hour.indexOf(Math.max(...card.by_hour));
  return slide(
    card,
    "restarts",
    html`
      <p class="kicker">${STORY.restartsKicker}</p>
      <h2 class="hero">${f.number(card.total)}</h2>
      <p class="line">
        ${card.total && top ? STORY.restartsMost(top.name, f.number(top.restarts)) : STORY.restartsNone}
      </p>
      ${card.busiest_day && card.busiest_day.restarts > 1
        ? html`<p class="fact">
            ${STORY.busiestDay(f.date(card.busiest_day.date), f.number(card.busiest_day.restarts))}
          </p>`
        : nothing}
      ${card.total > 2 ? html`<p class="fact">${STORY.favouriteHour(f.hour(peak))}</p>` : nothing}
      ${card.never.length ? html`<p class="fact">${STORY.never(someOf(card.never))}</p>` : nothing}
      ${containers ? html`<p class="fact">${containersLine(containers, f)}</p>` : nothing}
      ${network ? html`<p class="fact">${networkLine(network, f)}</p>` : nothing}
    `,
    html`${containers?.top.length || network?.top.length ? html`<p class="sub">${STORY.machinesTitle}</p>` : nothing}
      ${bars(card.machines, f)} ${groupBars(containers, STORY.containersTitle, f)}
      ${groupBars(network, STORY.networkTitle, f)}`,
    f,
  );
}

function groupBars(group: RestartGroup | null, title: string, f: Format): TemplateResult | typeof nothing {
  return group?.top.length ? html`<p class="sub">${title}</p>${bars(group.top.slice(0, 3), f)}` : nothing;
}

/** The summary's restarts number: the machines', else the containers' or the network gear's. */
export function restartsStat(card: RestartsCard, f: Format): [string, string] {
  const group = card.machines.length ? null : (card.containers ?? card.network ?? null);
  if (!group) return stat(f.number(card.total), STORY.summaryRestarts);
  return stat(
    f.number(group.total),
    group === card.containers ? STORY.summaryContainerRestarts : STORY.summaryNetworkRestarts,
  );
}

/** A lab Wrapped sees only containers or network gear of: the slide is about them. */
function groupsOnly(card: RestartsCard, main: RestartGroup, f: Format): TemplateResult {
  const containers = card.containers;
  const network = card.network ?? null;
  return slide(
    card,
    "restarts",
    html`
      <p class="kicker">${main === containers ? STORY.containersKicker : STORY.networkKicker}</p>
      <h2 class="hero">${f.number(main.total)}</h2>
      ${containers ? html`<p class="line">${containersLine(containers, f)}</p>` : nothing}
      ${network ? html`<p class=${containers ? "fact" : "line"}>${networkLine(network, f)}</p>` : nothing}
    `,
    containers && network
      ? html`${groupBars(containers, STORY.containersTitle, f)} ${groupBars(network, STORY.networkTitle, f)}`
      : bars(main.top, f),
    f,
  );
}

function containersLine(containers: RestartGroup, f: Format): string {
  const top = containers.top[0];
  return top
    ? STORY.containersMost(f.number(containers.total), top.name, f.number(top.restarts))
    : STORY.containersNone(f.number(containers.watched));
}

function networkLine(network: RestartGroup, f: Format): string {
  const top = network.top[0];
  return top
    ? STORY.networkMost(f.number(network.total), top.name, f.number(top.restarts))
    : STORY.networkNone(f.number(network.watched));
}

function bars(items: { name: string; restarts: number }[], f: Format): TemplateResult {
  const most = Math.max(1, ...items.map((item) => item.restarts));
  return html`<ul class="bars">
    ${items.map(
      (item) => html`<li>
        <span class="name">${item.name}</span>
        <span class="bar"><i style="width: ${(item.restarts / most) * 100}%"></i></span>
        <b>${f.number(item.restarts)}</b>
      </li>`,
    )}
  </ul>`;
}

function blocked(card: BlockedCard, f: Format): TemplateResult {
  return slide(
    card,
    "blocked",
    html`
      <p class="kicker">${STORY.blockedKicker}</p>
      <h2 class="hero">${f.big(card.total)}</h2>
      <p class="line">${STORY.blockedTitle(f.number(card.total))}</p>
      <p class="fact">${STORY.perDay(f.number(card.per_day))}</p>
      <p class="fact">${STORY.bestBlockedDay(f.date(card.best_day.date), f.number(card.best_day.blocked))}</p>
    `,
    html`<div class="shield" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm-1 14-4-4 1.4-1.4 2.6 2.6 5.6-5.6L18 9l-7 7Z" /></svg>
    </div>`,
    f,
  );
}

function media(card: MediaCard, f: Format): TemplateResult {
  const most = Math.max(1, ...card.by_month.map((hours) => hours ?? 0));
  const titles = card.titles ?? [];
  return slide(
    card,
    "media",
    html`
      <p class="kicker">${STORY.mediaKicker}</p>
      <h2 class="hero">${f.amount(card.hours)}</h2>
      <p class="line">${STORY.mediaTitle(f.amount(card.hours))}</p>
      ${card.hours >= 48 ? html`<p class="fact">${STORY.mediaDays(f.number(card.hours / 24, 1))}</p>` : nothing}
      <p class="fact">${STORY.bestMediaDay(f.date(card.best_day.date), f.number(card.best_day.hours, 1))}</p>
      ${titles.length === 1
        ? html`<p class="fact">${STORY.topTitle(titles[0].title, f.number(titles[0].hours, 1))}</p>`
        : nothing}
      ${titles.length > 1
        ? html`<p class="sub">${STORY.topTitles}</p>
            <ul class="list">
              ${titles.map((item) => html`<li><span>${item.title}</span><b>${f.number(item.hours, 1)} ${STORY.hoursUnit}</b></li>`)}
            </ul>`
        : nothing}
      ${card.servers.length > 1
        ? html`<p class="sub">${STORY.servers}</p>
            <ul class="list">
              ${card.servers.slice(0, TOP).map((server) => html`<li><span>${server.name}</span><b>${f.amount(server.hours)} ${STORY.hoursUnit}</b></li>`)}
            </ul>`
        : nothing}
    `,
    html`<div class="months">
      ${card.by_month.map(
        (hours, month) => html`<div class=${hours === null ? "month none" : "month"}>
          <span class="column"><i style="height: ${((hours ?? 0) / most) * 100}%"></i></span>
          <span class="label">${f.month(month)}</span>
        </div>`,
      )}
    </div>`,
    f,
  );
}

function power(card: PowerCard, f: Format): TemplateResult {
  const cuts = card.power_cuts;
  if (card.kwh === null || card.watts === null) return cutsOnly(card, cuts, f);
  const most = Math.max(0.001, ...card.by_month.map((kwh) => kwh ?? 0));
  const money = (value: number, digits: number) => f.money(value, card.currency ?? "", digits);
  return slide(
    card,
    "power",
    html`
      <p class="kicker">${STORY.powerKicker}</p>
      <h2 class="hero">${f.amount(card.kwh)}</h2>
      <p class="line">${STORY.powerTitle}</p>
      ${card.cost !== null ? html`<p class="fact">${STORY.powerCost(money(card.cost, 0), card.estimated)}</p>` : nothing}
      <p class="fact">${STORY.powerWatts(f.number(card.watts))}</p>
      ${card.average_price !== null
        ? html`<p class="fact">${STORY.powerPrice(money(card.average_price, 2))}</p>`
        : nothing}
      ${cuts ? html`<p class="fact">${cutsLine(cuts, f)}</p>` : nothing}
      ${card.meters.length > 1
        ? html`<ul class="list">
            ${card.meters.slice(0, TOP).map((meter) => html`<li><span>${meter.name}</span><b>${f.amount(meter.kwh)} kWh</b></li>`)}
          </ul>`
        : nothing}
    `,
    html`<div class="months">
      ${card.by_month.map(
        (kwh, month) => html`<div class=${kwh === null ? "month none" : "month"}>
          <span class="column"><i style="height: ${((kwh ?? 0) / most) * 100}%"></i></span>
          <span class="label">${f.month(month)}</span>
        </div>`,
      )}
    </div>`,
    f,
  );
}

/** A lab with a UPS but no meters picked: the slide is about its power cuts. */
function cutsOnly(card: PowerCard, cuts: PowerCard["power_cuts"], f: Format): TemplateResult {
  if (!cuts) return html``;
  return slide(
    card,
    "power",
    html`
      <p class="kicker">${STORY.cutsKicker}</p>
      <h2 class="hero">${f.number(cuts.count)}</h2>
      <p class="line">${STORY.cutsTitle(cuts.count)}</p>
      <p class="fact">${cutsLine(cuts, f)}</p>
    `,
    html`<div class="icon" aria-hidden="true"><ha-icon .icon=${"mdi:home-battery"}></ha-icon></div>`,
    f,
  );
}

function cutsLine(cuts: NonNullable<PowerCard["power_cuts"]>, f: Format): string {
  if (!cuts.count) return STORY.noCuts;
  const total = cuts.seconds ?? cuts.minutes * 60;
  const longest = cuts.longest_seconds ?? cuts.longest_minutes * 60;
  return STORY.cuts(f.number(cuts.count), duration(total, f), duration(longest, f));
}

/** Time on battery: seconds under a minute and a half, then minutes, then hours. */
function duration(seconds: number, f: Format): string {
  if (seconds < 90) return STORY.seconds(f.number(seconds));
  if (seconds < 90 * 60) return STORY.minutes(f.amount(seconds / 60));
  return STORY.hours(f.amount(seconds / 3600));
}

/** The summary's power number: kWh, or the power cuts in a lab without meters. */
export function powerStat(card: PowerCard, f: Format): [string, string] {
  return card.kwh !== null
    ? stat(f.amount(card.kwh), STORY.summaryPower)
    : stat(f.number(card.power_cuts?.count ?? 0), STORY.summaryCuts);
}

function personality(card: PersonalityCard, year: number, f: Format): TemplateResult {
  const who = PERSONALITIES[card.key] ?? PERSONALITIES.all_rounder;
  const reasons = card.traits
    .map((trait) => PERSONALITIES[trait.key]?.reason(f.number(trait.value, trait.value < 10 ? 1 : 0), year))
    .filter((reason): reason is string => Boolean(reason));
  return slide(
    null,
    "personality",
    html`
      <p class="kicker">${STORY.personalityKicker}</p>
      <h2 class="title">${who.name}</h2>
      <p class="line">${who.tagline}</p>
      ${reasons.length
        ? html`<p class="sub">${STORY.personalityWhy}</p>
            <ul class="list">
              ${reasons.map((reason) => html`<li><span>${reason}</span></li>`)}
            </ul>`
        : nothing}
    `,
    html`<div class="icon" aria-hidden="true"><ha-icon .icon=${who.icon}></ha-icon></div>`,
    f,
  );
}

/** The last slide: the year's headline numbers together. */
export function renderSummary(cards: StoryCard[], year: number, f: Format): TemplateResult {
  const stats: [string, string][] = [];
  const found = cards.find((card): card is PersonalityCard => card.card === "personality");
  const who = found ? (PERSONALITIES[found.key] ?? PERSONALITIES.all_rounder) : undefined;
  for (const card of cards) {
    if (card.card === "uptime") stats.push(uptimeStat(card, f));
    if (card.card === "restarts") stats.push(restartsStat(card, f));
    if (card.card === "blocked") stats.push(stat(f.big(card.total), STORY.summaryBlocked));
    if (card.card === "media") stats.push(stat(f.amount(card.hours), STORY.summaryMedia));
    if (card.card === "power") stats.push(powerStat(card, f));
    if (card.card === "intro" && card.machines) stats.push(stat(f.number(card.machines), STORY.summaryMachines));
  }
  return slide(
    null,
    "summary",
    html`
      <p class="kicker">${STORY.summaryKicker(year)}</p>
      <h2 class="title">${STORY.summaryTitle}</h2>
      ${who ? html`<p class="line who"><ha-icon .icon=${who.icon}></ha-icon>${who.name}</p>` : nothing}
    `,
    html`<div class="tiles">
      ${stats.map(
        ([value, label]) =>
          html`<div class="tile"><b class=${value.length > 6 ? "long" : ""}>${value}</b><span>${label}</span></div>`,
      )}
    </div>`,
    f,
  );
}
