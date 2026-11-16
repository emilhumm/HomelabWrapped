/**
 * The share image: one portrait 9:16 picture of the year, drawn on a canvas in
 * the browser, so nothing leaves the network. Machine names (hostnames) are
 * left out unless the user asks for them.
 */

import { Format } from "./format";
import { powerStat, restartsStat, stat, uptimeStat } from "./slides";
import { PERSONALITIES, SHARE, STORY } from "./text";
import type { CardsResponse, PersonalityCard, StoryCard, UptimeCard } from "./types";

export const WIDTH = 1080;
export const HEIGHT = 1920;
const MARGIN = 88;
const FONT = 'Roboto, "Segoe UI", "Helvetica Neue", Arial, sans-serif';

export interface ShareOptions {
  /** Show machine names, such as the one with the longest streak. */
  names: boolean;
}

export function drawShareImage(
  canvas: HTMLCanvasElement,
  data: CardsResponse,
  options: ShareOptions,
  language: string,
): void {
  const f = new Format(language);
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const background = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT);
  background.addColorStop(0, "#312e81");
  background.addColorStop(0.55, "#6d28d9");
  background.addColorStop(1, "#be185d");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  ctx.fillStyle = "#fff";
  ctx.textBaseline = "alphabetic";

  let y = 150;
  ctx.font = `700 34px ${FONT}`;
  spaced(ctx, SHARE.brand.toUpperCase(), MARGIN, y, 6);
  y += 190;
  ctx.font = `800 200px ${FONT}`;
  ctx.fillText(String(data.year), MARGIN - 8, y);

  const found = find<PersonalityCard>(data.cards, "personality");
  if (found) {
    const who = PERSONALITIES[found.key] ?? PERSONALITIES.all_rounder;
    y += 110;
    ctx.globalAlpha = 0.85;
    ctx.font = `600 34px ${FONT}`;
    ctx.fillText(STORY.personalityKicker, MARGIN, y);
    ctx.globalAlpha = 1;
    y += 92;
    ctx.font = `800 88px ${FONT}`;
    ctx.fillText(who.name, MARGIN, y, WIDTH - 2 * MARGIN);
    y += 64;
    ctx.font = `500 38px ${FONT}`;
    y = wrap(ctx, who.tagline, MARGIN, y, WIDTH - 2 * MARGIN, 50);
  }

  y += 70;
  y = tiles(ctx, stats(data.cards, f), y);

  // The year grid sits at the bottom, above the footer, whatever the tiles above take.
  const uptime = find<UptimeCard>(data.cards, "uptime");
  if (uptime?.longest) {
    const top = HEIGHT - 190 - gridHeight(uptime);
    if (options.names) {
      ctx.font = `500 34px ${FONT}`;
      const best = uptime.longest;
      // Under the tiles even when a short year's grid leaves little room above it.
      const line = Math.max(top - 110, y + 64);
      ctx.fillText(SHARE.longestBy(best.name, STORY.days(f.amount(best.days))), MARGIN, line, WIDTH - 2 * MARGIN);
    }
    ctx.font = `600 32px ${FONT}`;
    ctx.fillText(STORY.gridTitle, MARGIN, top - 28);
    grid(ctx, uptime, top);
  }

  ctx.fillStyle = "#fff";
  ctx.globalAlpha = 0.75;
  ctx.font = `500 30px ${FONT}`;
  ctx.fillText(SHARE.footer, MARGIN, HEIGHT - 90);
  ctx.globalAlpha = 1;
}

/** Share on devices that can (phones), else download. */
export async function shareOrDownload(canvas: HTMLCanvasElement, year: number): Promise<void> {
  const name = `homelab-wrapped-${year}.png`;
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("no image");
  const file = new File([blob], name, { type: "image/png" });
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: SHARE.brand });
      return;
    } catch (err) {
      // The user closed the share sheet: done. Anything else (Safari refuses a share that
      // doesn't follow the tap at once, and making the PNG takes a moment): download it.
      if ((err as Error)?.name === "AbortError") throw err;
    }
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

function find<T extends StoryCard>(cards: StoryCard[], id: T["card"]): T | undefined {
  return cards.find((card): card is T => card.card === id);
}

function stats(cards: StoryCard[], f: Format): [string, string][] {
  const found: [string, string][] = [];
  for (const card of cards) {
    if (card.card === "uptime") found.push(uptimeStat(card, f));
    if (card.card === "restarts") found.push(restartsStat(card, f));
    if (card.card === "blocked") found.push(stat(f.big(card.total), STORY.summaryBlocked));
    if (card.card === "media") found.push(stat(f.amount(card.hours), STORY.summaryMedia));
    if (card.card === "power") found.push(powerStat(card, f));
  }
  return found.slice(0, 6);
}

/** Two columns of number tiles; returns the y below them. */
function tiles(ctx: CanvasRenderingContext2D, items: [string, string][], top: number): number {
  const gap = 28;
  const width = (WIDTH - 2 * MARGIN - gap) / 2;
  const height = 190;
  items.forEach(([value, label], index) => {
    const x = MARGIN + (index % 2) * (width + gap);
    const y = top + Math.floor(index / 2) * (height + gap);
    ctx.fillStyle = "rgba(255, 255, 255, 0.14)";
    rounded(ctx, x, y, width, height, 28);
    ctx.fillStyle = "#fff";
    ctx.font = `800 84px ${FONT}`;
    ctx.fillText(value, x + 32, y + 104, width - 64);
    ctx.font = `500 32px ${FONT}`;
    ctx.globalAlpha = 0.9;
    ctx.fillText(label, x + 32, y + 152, width - 64);
    ctx.globalAlpha = 1;
  });
  return top + Math.ceil(items.length / 2) * (height + gap);
}

function gridLayout(uptime: UptimeCard): { offset: number; step: number } {
  const start = new Date(`${uptime.grid.start}T00:00:00`);
  const offset = (start.getDay() + 6) % 7;
  const weeks = Math.ceil((offset + uptime.grid.restarts.length) / 7);
  return { offset, step: Math.min(34, (WIDTH - 2 * MARGIN) / Math.max(weeks, 1)) };
}

function gridHeight(uptime: UptimeCard): number {
  return 7 * gridLayout(uptime).step;
}

/** The uptime year grid, as on the uptime card; returns the y below it. */
function grid(ctx: CanvasRenderingContext2D, uptime: UptimeCard, top: number): number {
  const { offset, step } = gridLayout(uptime);
  const size = step * 0.8;
  uptime.grid.restarts.forEach((restarts, day) => {
    const cell = offset + day;
    ctx.fillStyle =
      restarts === null
        ? "rgba(255, 255, 255, 0.15)"
        : restarts === 0
          ? "#34d399"
          : restarts === 1
            ? "#fde68a"
            : restarts === 2
              ? "#fbbf24"
              : "#f97316";
    rounded(ctx, MARGIN + Math.floor(cell / 7) * step, top + (cell % 7) * step, size, size, size / 5);
  });
  return top + 7 * step;
}

function rounded(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
): void {
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, width, height, radius);
  } else {
    // Safari before 16 and older wall tablets have no roundRect.
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    ctx.closePath();
  }
  ctx.fill();
}

/** Text with letter spacing, for the small capitals. */
function spaced(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, spacing: number): void {
  let left = x;
  for (const char of text) {
    ctx.fillText(char, left, y);
    left += ctx.measureText(char).width + spacing;
  }
}

/** Wrapped text; returns the y of the last line. */
function wrap(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  width: number,
  lineHeight: number,
): number {
  let line = "";
  for (const word of text.split(" ")) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > width && line) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = next;
    }
  }
  ctx.fillText(line, x, y);
  return y;
}
