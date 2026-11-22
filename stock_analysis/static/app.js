const form = document.getElementById("desk-form");
const report = document.getElementById("report");
const errorBox = document.getElementById("form-error");
const exchange = document.getElementById("exchange");
const priceHint = document.getElementById("price-hint");

const CURRENCY = {
  NYSE: "USD",
  NASDAQ: "USD",
  "NYSE American": "USD",
  "NYSE Arca": "USD",
  Cboe: "USD",
  NSE: "INR",
  BSE: "INR",
};

exchange.addEventListener("change", () => {
  const currency = CURRENCY[exchange.value];
  priceHint.textContent = currency
    ? `Optional. If you type a ${currency} print, it is labeled user input and is not a quote.`
    : "If you type one, it is labeled user input. It is not treated as a quote.";
});

form.addEventListener("reset", () => {
  errorBox.hidden = true;
  priceHint.textContent = "If you type one, it is labeled user input. It is not treated as a quote.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  const payload = {
    ticker: document.getElementById("ticker").value,
    exchange: exchange.value,
    horizon: document.getElementById("horizon").value,
    risk_tolerance: document.getElementById("risk_tolerance").value,
    last_price: document.getElementById("last_price").value,
  };
  const submit = form.querySelector("button[type=submit]");
  submit.disabled = true;
  try {
    const response = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      showError(body.error || "The note could not be built.");
      return;
    }
    render(body);
    if (window.matchMedia("(max-width: 980px)").matches) {
      report.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (_error) {
    showError("The desk could not be reached.");
  } finally {
    submit.disabled = false;
  }
});

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
}

function render(note) {
  report.replaceChildren();

  const identity = el("div", "identity");
  const titleBlock = el("div");
  titleBlock.append(
    el("p", "kicker", "Equity pressure note"),
    el("h2", null, `${note.identity.ticker} · ${note.identity.exchange}`),
    el(
      "p",
      "identity-meta",
      `${note.identity.horizon_label} · ${note.identity.risk_label} risk`,
    ),
  );
  const clock = el("div", "clock");
  clock.append(el("p", null, note.generated_note));
  const stamped = note.generated_at.replace("T", " ").replace("Z", " UTC");
  const time = el("time", null, stamped);
  time.dateTime = note.generated_at;
  clock.append(time);
  identity.append(titleBlock, clock);

  report.append(
    identity,
    el("p", "opening", note.opening),
    el("p", "weighting", note.weighting),
    el("p", "disclaimer", note.disclaimer),
    qualityBlock(note),
    windowsBlock(note),
  );

  for (const pillar of note.pillars) {
    report.append(renderPillar(pillar));
  }

  const sources = el(
    "p",
    "sources",
    note.sources_called.length === 0
      ? "Sources called: none. No market-data feed and no model were used."
      : `Sources called: ${note.sources_called.join(", ")}`,
  );
  report.append(sources);
}

function qualityBlock(note) {
  const block = el("section", "block");
  block.append(el("p", "section-label", "Data quality"), el("h3", null, "Read this before the figures"));
  const grid = el("div", "quality");
  for (const item of note.data_quality) {
    const article = el("article");
    article.append(el("h4", null, item.title), el("p", null, item.text));
    grid.append(article);
  }
  block.append(grid);
  return block;
}

function windowsBlock(note) {
  const block = el("section", "block");
  block.append(el("p", "section-label", "Freshness windows"), el("h3", null, "When a figure is stale"));
  const list = el("ul", "windows");
  for (const item of note.freshness_windows) {
    const row = el("li");
    row.append(el("strong", null, item.series), el("span", null, item.window));
    list.append(row);
  }
  block.append(list);
  return block;
}

function renderPillar(pillar) {
  const section = el("section", "pillar");
  section.append(
    el("p", "kicker", `${pillar.number}. ${pillar.kicker}`),
    el("h3", null, pillar.title),
  );
  if (pillar.figures) {
    section.append(figureTable(pillar.figures));
  }
  if (pillar.groups) {
    const groups = el("div", "groups");
    for (const group of pillar.groups) {
      const column = el("div", "group");
      column.append(el("h4", null, group.title));
      for (const bullet of group.bullets) {
        const item = el("div", "bullet");
        item.append(el("p", null, bullet.text), el("p", "cites", bullet.cites));
        column.append(item);
      }
      groups.append(column);
    }
    section.append(groups);
  }
  section.append(interpretation(pillar.interpretation));
  return section;
}

function figureTable(figures) {
  const wrap = el("div", "figures");
  wrap.append(figureRow(["Field", "Value", "Source", "As of"], true));
  for (const figure of figures) wrap.append(figureRow(figure, false));
  return wrap;
}

function figureRow(figure, header) {
  const row = el("div", header ? "figure figure-head" : "figure");
  if (header) {
    for (const label of figure) row.append(el("div", null, label));
    return row;
  }
  const valueCell = el("div", "cell");
  valueCell.append(el("span", "caption", "Value"));
  const valueLine = el("div", "value-line");
  const shown = figure.unit ? `${figure.value} ${figure.unit}` : figure.value;
  valueLine.append(el("span", "value", shown));
  valueLine.append(el("span", `pill ${figure.status}`, figure.status_label));
  if (figure.stale) valueLine.append(el("span", "stale-flag", "Stale"));
  valueCell.append(valueLine);

  row.append(
    labeled("Field", figure.label, "label"),
    valueCell,
    labeled("Source", figure.source || "none"),
    labeled("As of", figure.as_of || "none"),
  );
  row.append(el("p", "freshness", `Freshness: ${figure.freshness}`));
  row.append(el("p", "note", figure.note));
  return row;
}

function labeled(caption, text, extra) {
  const cell = el("div", extra ? `cell ${extra}` : "cell");
  cell.append(el("span", "caption", caption), el("span", null, text));
  return cell;
}

function interpretation(text) {
  const block = el("div", "interpretation");
  block.append(el("strong", null, "Interpretation"), document.createTextNode(text));
  return block;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
