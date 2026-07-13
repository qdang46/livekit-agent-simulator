import { LEGEND_ORDER, markerTitle } from "../lib/constants";
import type { Marker, MarkerType } from "../types";

export function mountLegend(el: HTMLElement, markers: Marker[]): void {
  el.innerHTML = "";
  const present = new Set(markers.map((m) => m.type));
  const types: MarkerType[] = LEGEND_ORDER.filter((t) => present.has(t));
  for (const m of markers) {
    if (!types.includes(m.type)) types.push(m.type);
  }
  if (!types.length) {
    el.innerHTML = `<span class="muted">No behavior or tool markers in this run.</span>`;
    return;
  }
  for (const t of types) {
    const item = document.createElement("span");
    item.className = "legend-item";
    item.innerHTML = `<span class="swatch ${t}"></span>`;
    const label = document.createElement("span");
    label.textContent = markerTitle(t);
    item.appendChild(label);
    el.appendChild(item);
  }
}
