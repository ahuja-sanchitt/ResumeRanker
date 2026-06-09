function Bar({ label, value, tone }) {
  return (
    <div className="bar">
      <div className="bar__head">
        <span>{label}</span>
        <span className="bar__val">{value}</span>
      </div>
      <div className="bar__track">
        <div className={`bar__fill bar__fill--${tone}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function Chips({ items, tone }) {
  if (!items?.length) return <p className="muted">None identified.</p>;
  return (
    <div className="chips">
      {items.map((s, i) => (
        <span key={i} className={`chip chip--${tone}`}>{s}</span>
      ))}
    </div>
  );
}

export default function ScoreBreakdown({ result }) {
  const { final_score, embedding_score, llm_fit_score, cached } = result;
  return (
    <div className="result">
      <div className="scorecard">
        <div className="scorecard__final">
          <div className="scorecard__num">{final_score}</div>
          <div className="scorecard__label">Match score</div>
          {cached && <span className="badge">cached</span>}
        </div>
        <div className="scorecard__bars">
          <Bar label="Embedding similarity (objective)" value={embedding_score} tone="blue" />
          <Bar label="LLM fit judgement" value={llm_fit_score} tone="violet" />
        </div>
      </div>

      <div className="grid2">
        <section>
          <h3>Matched skills</h3>
          <Chips items={result.matched_skills} tone="good" />
        </section>
        <section>
          <h3>Missing skills</h3>
          <Chips items={result.missing_skills} tone="bad" />
        </section>
      </div>

      <div className="grid2">
        <section>
          <h3>Strengths</h3>
          {result.strengths?.length ? (
            <ul className="list">{result.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          ) : <p className="muted">—</p>}
        </section>
        <section>
          <h3>Gaps</h3>
          {result.gaps?.length ? (
            <ul className="list">{result.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul>
          ) : <p className="muted">—</p>}
        </section>
      </div>

      {result.feedback && (
        <section>
          <h3>Feedback</h3>
          <p className="feedback">{result.feedback}</p>
        </section>
      )}
    </div>
  );
}
