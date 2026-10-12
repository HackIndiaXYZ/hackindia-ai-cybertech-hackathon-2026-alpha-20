import { Card } from "../components/Common";

export default function About() {
  return (
    <>
      <h1>Safety &amp; about</h1>
      <div className="emergency-banner static" role="note">
        <strong>▲ In an emergency, call your local emergency number immediately (112 in India).</strong>
        <p>Chest pain, trouble breathing, signs of stroke, fainting, seizures, severe bleeding, a severe allergic reaction, poisoning, or thoughts of self-harm need urgent in-person help. Do not wait for this tool.</p>
      </div>
      <Card title="What MedTriage AI is">
        <p>A hackathon prototype for rural clinics that supports <strong>clinical documentation and preliminary triage</strong>. A health worker enters symptoms by text or voice and receives a structured summary, a preliminary urgency category and a PDF report for a clinician.</p>
      </Card>
      <Card title="What it is not">
        <ul className="list">
          <li>It does <strong>not diagnose</strong>, prescribe, or give medication doses or treatment plans.</li>
          <li>It is <strong>not clinically validated</strong>; no accuracy, sensitivity or specificity figures exist.</li>
          <li>It does not replace a qualified clinician. A clinician must review every case.</li>
          <li>It makes no regulatory or privacy-compliance claims (such as HIPAA).</li>
        </ul>
      </Card>
      <Card title="How urgency is decided">
        <ul className="list">
          <li><strong>Rule-based:</strong> a small, transparent set of keyword rules with negation handling ("no chest pain" is not chest pain). They are preliminary demonstration logic needing clinician review.</li>
          <li><strong>Conservative:</strong> unclear or conflicting statements are treated as possibly present. Words like "mild" never downgrade a warning sign.</li>
          <li><strong>AI can only escalate:</strong> an AI model may write the summary and may raise urgency, never lower it. Symptoms it invents are discarded.</li>
          <li><strong>UNDETERMINED</strong> means the tool could not assess the text. It is <em>not</em> a sign of low risk.</li>
          <li>Voice transcripts are machine-generated and can be wrong. Always check them.</li>
        </ul>
      </Card>
      <Card title="Data">
        <p>Use fictional demonstration data only. Do not enter real patient information. When an AI key is configured, report text is sent to the AI provider (Groq). The queue and reports are stored in a local database without authentication; do not expose this prototype publicly.</p>
      </Card>
    </>
  );
}
