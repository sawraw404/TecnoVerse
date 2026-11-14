import type { Opportunity, PriorityType } from "./types";

/** ISO date or datetime -> YYYY-MM-DD, the format the sources use. */
export function day(value: string | null | undefined): string {
  return value ? value.slice(0, 10) : "not stated";
}

export const TYPE_LABEL: Record<PriorityType, string> = {
  funding: "Funding",
  event: "Events",
  testbed: "Testbeds",
};

export const DATE_LABEL: Record<string, string> = {
  funding: "Deadline",
  event: "Starts",
  testbed: "Date",
  news: "Published",
};

export function keyDate(o: Opportunity): string | null {
  return o.deadline ?? o.start_date;
}

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
