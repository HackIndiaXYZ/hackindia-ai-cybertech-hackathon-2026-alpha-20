const dtf = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
export function formatTime(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "-" : dtf.format(d);
}

export const URGENCY = {
  emergency:    { label: "EMERGENCY",    glyph: "▲", cls: "u-emergency", hint: "Potential life-threatening warning sign reported." },
  urgent:       { label: "URGENT",       glyph: "◆", cls: "u-urgent",    hint: "Prompt assessment by a healthcare professional advised." },
  routine:      { label: "ROUTINE",      glyph: "●", cls: "u-routine",   hint: "Only common symptoms recognised. Not a diagnosis." },
  undetermined: { label: "UNDETERMINED", glyph: "?", cls: "u-undetermined", hint: "Could not be assessed. This does NOT mean low risk." },
};
export const URGENCY_ORDER = ["emergency", "urgent", "routine", "undetermined"];

export const AGE_GROUPS = [
  ["unspecified", "Not specified"], ["infant", "Infant (under 1 year)"], ["child", "Child"],
  ["adult", "Adult"], ["older_adult", "Older adult"],
];
export const STATUS_LABEL = { waiting: "Waiting", in_assessment: "In assessment", seen: "Seen" };

export const EXAMPLES = [
  "Synthetic example: I have had a cough, runny nose and mild fever for 2 days.",
  "Synthetic example: I have no chest pain, but I have a headache and feel dizzy since morning.",
  "Synthetic example: My relative has chest pain and is finding it hard to breathe.",
];

export function describeMode(r) {
  if (r.mode === "llm_groq_with_rules") return `AI-assisted summary (${r.ai_model || "model"}) + rule-based urgency`;
  if (r.mode === "rules_only_fallback") return "Rules only - the AI service failed, so no AI output was used";
  return "Rules only - AI not configured, no AI output was used";
}
