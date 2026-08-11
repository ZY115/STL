import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, "../../../..");
const OUT_DIR = path.join(SCRIPT_DIR, "rendered");
const FINAL_PPTX = path.join(REPO_ROOT, "docs/slides/stage1_current_progress_slides.pptx");

const C = {
  orange: "#F37021",
  orangeDark: "#C84E0B",
  orangeSoft: "#FFF0E7",
  blue: "#2F6FAE",
  blueSoft: "#EAF3FF",
  green: "#2E7D4F",
  greenSoft: "#EAF7EF",
  yellow: "#A66A00",
  yellowSoft: "#FFF7D8",
  purple: "#6650A4",
  purpleSoft: "#F0ECFF",
  red: "#B53A2D",
  redSoft: "#FFF0EC",
  gray50: "#FAFAFA",
  gray100: "#F4F4F4",
  gray200: "#E5E5E5",
  gray400: "#9A9A9A",
  gray600: "#666666",
  gray800: "#282828",
  black: "#151515",
  white: "#FFFFFF",
};

const FONT = "Aptos";
const FONT_BUMP = 2;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, text, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: options.name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontFamily: FONT,
    fontSize: (options.fontSize ?? 24) + FONT_BUMP,
    color: options.color ?? C.gray800,
    bold: options.bold ?? false,
    alignment: options.align ?? "left",
  };
  return shape;
}

function addRect(slide, x, y, w, h, options = {}) {
  return slide.shapes.add({
    geometry: options.geometry ?? "roundRect",
    name: options.name,
    position: { left: x, top: y, width: w, height: h },
    fill: options.fill ?? C.white,
    line: {
      style: "solid",
      fill: options.line ?? C.gray200,
      width: options.lineWidth ?? 1,
    },
  });
}

function addTitle(slide, title, page) {
  addText(slide, title, 72, 34, 1110, 58, { fontSize: 35, bold: true, color: C.black, name: `title-${page}` });
  addText(slide, String(page), 1190, 42, 26, 28, { fontSize: 16, color: C.gray400, align: "right" });
}

function addFooter(slide, text = "Language-Grounded STL Safe RL | Stage I progress") {
  addText(slide, text, 72, 690, 800, 20, { fontSize: 11, color: C.gray400 });
}

function addLabel(slide, text, x, y, w, color, fill) {
  addRect(slide, x, y, w, 30, { fill, line: color, lineWidth: 1 });
  addText(slide, text, x + 8, y + 5, w - 16, 18, { fontSize: 12, bold: true, color, align: "center" });
}

function addArrow(slide, x, y, w = 38, h = 24, color = C.orange) {
  return addRect(slide, x, y, w, h, { geometry: "rightArrow", fill: color, line: color, lineWidth: 0 });
}

function addStageNode(slide, x, y, w, h, title, body, options = {}) {
  const titleHeight = options.titleHeight ?? 32;
  const bodyTop = options.bodyTop ?? 56;
  addRect(slide, x, y, w, h, {
    fill: options.fill ?? C.white,
    line: options.line ?? C.gray200,
    lineWidth: options.lineWidth ?? 1,
  });
  addText(slide, title, x + 16, y + 16, w - 32, titleHeight, {
    fontSize: options.titleSize ?? 20,
    bold: true,
    color: options.titleColor ?? C.black,
    align: options.align ?? "left",
  });
  addText(slide, body, x + 16, y + bodyTop, w - 32, h - bodyTop - 12, {
    fontSize: options.bodySize ?? 16,
    color: options.bodyColor ?? C.gray600,
    align: options.align ?? "left",
  });
}

function addNotes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.map((s) => `- ${s}`).join("\n")}`);
}

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

// Slide 1
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "The Complete Goal: Language to Safer RL", 1);

  addRect(slide, 116, 118, 1048, 112, { fill: C.orangeSoft, line: C.orange, lineWidth: 2 });
  addText(slide, "\"Reach the goal. If you get too close to a hazard, return to a safe distance within the allowed time.\"", 156, 146, 968, 58, { fontSize: 25, bold: true, color: C.black, align: "center" });

  const flow = [
    ["User\ncommand", C.redSoft, C.red],
    ["Translate safety\nto STL", C.yellowSoft, C.yellow],
    ["Monitor the\ntrajectory", C.blueSoft, C.blue],
    ["Produce an\nRL cost", C.purpleSoft, C.purple],
    ["Learn task +\nsafer behavior", C.greenSoft, C.green],
  ];
  const xs = [70, 310, 550, 790, 1030];
  for (let i = 0; i < 4; i += 1) addArrow(slide, xs[i] + 186, 330, 46, 28, C.orange);
  flow.forEach(([label, fill, color], i) => {
    addRect(slide, xs[i], 278, 186, 132, { fill, line: color, lineWidth: 1.5 });
    addText(slide, label, xs[i] + 14, 316, 158, 64, { fontSize: 19, bold: true, color: C.black, align: "center" });
  });

  addRect(slide, 154, 474, 972, 112, { fill: C.gray50, line: C.gray200, lineWidth: 1 });
  addText(slide, "\"Too close -> recover in time\" becomes a rule, a trajectory check, a safety cost, and finally a training signal.", 192, 505, 896, 58, { fontSize: 22, bold: true, color: C.orangeDark, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/PROJECT_CONTEXT.md",
    "/Users/yuhang/Downloads/STL/README.md",
  ]);
}

// Slide 2
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "Why the Research Is Split into Three Stages", 2);

  addText(slide, "The full chain contains three independent questions:", 86, 116, 790, 34, { fontSize: 22, bold: true, color: C.gray800 });
  addStageNode(slide, 70, 164, 350, 132, "1. STL execution", "Can a correct STL rule be monitored and used by RL?", { fill: C.orangeSoft, line: C.orange, titleColor: C.orangeDark, titleSize: 21, bodySize: 17 });
  addStageNode(slide, 465, 164, 350, 132, "2. Language translation", "Can natural language be translated into STL accurately?", { fill: C.yellowSoft, line: C.yellow, titleColor: C.yellow, titleSize: 21, bodySize: 17 });
  addStageNode(slide, 860, 164, 350, 132, "3. Broader setting", "What changes with vague language, complex environments, and real robots?", { fill: C.blueSoft, line: C.blue, titleColor: C.blue, titleSize: 21, bodySize: 17 });

  addText(slide, "If one end-to-end experiment fails, the cause is ambiguous:", 86, 346, 800, 34, { fontSize: 22, bold: true, color: C.gray800 });
  const failures = [
    ["Translation\nwas wrong", C.redSoft, C.red],
    ["Grounding\nwas wrong", C.blueSoft, C.blue],
    ["Monitor\nwas wrong", C.greenSoft, C.green],
    ["Cost never\nreached RL", C.purpleSoft, C.purple],
    ["RL did not\nlearn", C.gray100, C.gray600],
  ];
  const fxs = [70, 306, 542, 778, 1014];
  failures.forEach(([label, fill, color], i) => {
    addRect(slide, fxs[i], 398, 196, 102, { fill, line: color, lineWidth: 1.25 });
    addText(slide, label, fxs[i] + 14, 426, 168, 52, { fontSize: 18, bold: true, color: C.black, align: "center" });
  });
  addText(slide, "Separating the stages makes each failure interpretable.", 224, 560, 832, 44, { fontSize: 25, bold: true, color: C.orangeDark, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/PROJECT_CONTEXT.md",
    "/Users/yuhang/Downloads/STL/docs/stage1_plan.md",
  ]);
}

// Slide 3
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "Each Stage Answers One Question", 3);

  addArrow(slide, 408, 286, 56, 32, C.orange);
  addArrow(slide, 816, 286, 56, 32, C.orange);
  addStageNode(slide, 70, 160, 338, 290, "Stage I: Gold STL", "A human provides one correct STL rule.\n\nValidate STL -> monitor -> cost -> Safe RL.", { fill: C.orangeSoft, line: C.orange, lineWidth: 3, titleColor: C.orangeDark, titleSize: 24, bodySize: 19 });
  addLabel(slide, "CURRENT", 176, 124, 126, C.orangeDark, C.orangeSoft);
  addStageNode(slide, 464, 160, 338, 290, "Stage II: Controlled NL", "Use clear commands with explicit objects, distances, and deadlines.\n\nValidate NL -> STL -> Safe RL.", { fill: C.yellowSoft, line: C.yellow, titleColor: C.yellow, titleSize: 22, bodySize: 18 });
  addStageNode(slide, 872, 160, 338, 290, "Stage III: Broader tests", "Add vague language, moving hazards, sensing error, more STL structures, and more complex environments.", { fill: C.blueSoft, line: C.blue, titleColor: C.blue, titleSize: 22, bodySize: 18 });

  addRect(slide, 210, 520, 860, 82, { fill: C.gray50, line: C.gray200, lineWidth: 1 });
  addText(slide, "Current work is Stage I: language translation is intentionally excluded.", 246, 544, 788, 38, { fontSize: 22, bold: true, color: C.black, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/README.md",
    "/Users/yuhang/Downloads/STL/DECISIONS.md",
  ]);
}

// Slide 4
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "Stage I Tests the Downstream Chain First", 4);

  addRect(slide, 112, 116, 1056, 126, { fill: C.purpleSoft, line: C.purple, lineWidth: 1.5 });
  addText(slide, "Can one correct STL rule monitor trajectories, produce a safety cost, and help Safe RL reduce temporal violations while still reaching the goal?", 154, 146, 972, 72, { fontSize: 23, bold: true, color: C.black, align: "center" });

  addArrow(slide, 390, 326, 52, 28, C.green);
  addArrow(slide, 794, 326, 52, 28, C.green);
  addArrow(slide, 390, 512, 52, 28, C.orange);
  addArrow(slide, 794, 512, 52, 28, C.gray600);

  const topSteps = [
    [70, "1. Environment\nand signal", "DONE", C.green, C.greenSoft],
    [474, "2. Rule and\nparameters", "DONE", C.green, C.greenSoft],
    [878, "3. Monitor and\nSTL cost", "DONE", C.green, C.greenSoft],
  ];
  topSteps.forEach(([x, label, status, color, fill]) => {
    addRect(slide, x, 276, 320, 132, { fill, line: color, lineWidth: 1.5 });
    addLabel(slide, status, x + 98, 290, 124, color, C.white);
    addText(slide, label, x + 26, 336, 268, 52, { fontSize: 19, bold: true, color: C.black, align: "center" });
  });
  const bottomSteps = [
    [70, "4. OmniSafe\nwrapper", "NEXT", C.orangeDark, C.orangeSoft],
    [474, "5. Train three\nagents", "LATER", C.gray600, C.gray100],
    [878, "6. Compare safety\nand task performance", "LATER", C.gray600, C.gray100],
  ];
  bottomSteps.forEach(([x, label, status, color, fill]) => {
    addRect(slide, x, 462, 320, 132, { fill, line: color, lineWidth: status === "NEXT" ? 3 : 1.5 });
    addLabel(slide, status, x + 98, 476, 124, color, C.white);
    addText(slide, label, x + 26, 522, 268, 52, { fontSize: 19, bold: true, color: C.black, align: "center" });
  });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/docs/CURRENT_STAGE1_STATUS.md",
    "/Users/yuhang/Downloads/STL/docs/stage1_plan.md",
  ]);
}

// Slide 5
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "The Benchmark Fixes the Environment and Signal", 5);

  addText(slide, "SafetyPointGoal1-v0", 84, 124, 520, 44, { fontSize: 27, bold: true, color: C.orangeDark });
  addText(slide, "A simple 2D navigation task", 84, 170, 520, 34, { fontSize: 20, color: C.gray600 });
  addRect(slide, 72, 224, 540, 310, { fill: C.gray50, line: C.gray200, lineWidth: 1 });
  addText(slide, "The environment contains", 104, 252, 440, 36, { fontSize: 22, bold: true, color: C.gray800 });
  addText(slide, "- one 2D Point agent\n- one goal\n- several static hazards\n- task reward for reaching the goal\n- native Safety-Gymnasium hazard cost", 112, 304, 440, 184, { fontSize: 20, color: C.black });

  addRect(slide, 668, 224, 540, 310, { fill: C.blueSoft, line: C.blue, lineWidth: 1.5 });
  addText(slide, "Our safety signal", 704, 252, 420, 36, { fontSize: 22, bold: true, color: C.blue });
  addText(slide, "d_t = distance from the agent\nto the nearest hazard center", 704, 316, 432, 74, { fontSize: 27, bold: true, color: C.black, align: "center" });
  addText(slide, "At every step, the monitor receives one distance value from the environment.", 718, 430, 404, 62, { fontSize: 19, color: C.gray600, align: "center" });

  addText(slide, "This fixes what is measured before we ask whether RL can learn from it.", 210, 574, 860, 42, { fontSize: 23, bold: true, color: C.orangeDark, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/docs/environment_inspection.md",
    "/Users/yuhang/Downloads/STL/src/safety_stl/signals.py",
    "/Users/yuhang/Downloads/STL/references/code-notes/safety-gymnasium-selected/goal_level1.py",
  ]);
}

// Slide 6
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "One Rule Defines the Recovery Task", 6);

  addRect(slide, 104, 112, 1072, 112, { fill: C.orangeSoft, line: C.orange, lineWidth: 1.5 });
  addText(slide, "When the agent first enters the warning zone, it must return to the safe distance before the deadline.", 154, 144, 972, 56, { fontSize: 24, bold: true, color: C.black, align: "center" });

  addText(slide, "Fixed parameters", 86, 270, 300, 34, { fontSize: 22, bold: true, color: C.gray800 });
  addText(slide, "warning distance = 0.45\nsafe distance = 0.55\ndeadline = 79 steps", 94, 326, 330, 124, { fontSize: 23, bold: true, color: C.orangeDark });
  addText(slide, "After the first d_t < 0.45, the agent must achieve d_t >= 0.55 within 79 steps.", 82, 486, 380, 76, { fontSize: 19, color: C.gray600, align: "center" });

  addText(slide, "Two distances create a recovery buffer", 520, 270, 650, 34, { fontSize: 22, bold: true, color: C.gray800 });
  addStageNode(slide, 520, 318, 650, 86, "d_t < 0.45", "Warning begins", { fill: C.redSoft, line: C.red, titleColor: C.red, titleSize: 19, bodySize: 16, titleHeight: 24, bodyTop: 44 });
  addStageNode(slide, 520, 420, 650, 86, "0.45 <= d_t < 0.55", "Recovery is still pending", { fill: C.yellowSoft, line: C.yellow, titleColor: C.yellow, titleSize: 19, bodySize: 16, titleHeight: 24, bodyTop: 44 });
  addStageNode(slide, 520, 522, 650, 86, "d_t >= 0.55", "Recovery is complete", { fill: C.greenSoft, line: C.green, titleColor: C.green, titleSize: 19, bodySize: 16, titleHeight: 24, bodyTop: 44 });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/configs/stage1_rule.yaml",
    "/Users/yuhang/Downloads/STL/docs/stage1_rule_monitor_spec.md",
    "/Users/yuhang/Downloads/STL/docs/rule_calibration_report.md",
  ]);
}

// Slide 7
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "The Monitor Turns Recovery into an RL Cost", 7);

  addText(slide, "The monitor reads d_t at every step and keeps one recovery state:", 82, 118, 900, 34, { fontSize: 21, bold: true, color: C.gray800 });
  addArrow(slide, 398, 230, 58, 30, C.orange);
  addArrow(slide, 824, 230, 58, 30, C.orange);
  addStageNode(slide, 70, 180, 328, 156, "INACTIVE", "No recovery obligation is open.", { fill: C.gray100, line: C.gray400, titleSize: 22, bodySize: 18, align: "center" });
  addStageNode(slide, 456, 180, 368, 156, "PENDING", "The warning zone was entered; the deadline is running.", { fill: C.yellowSoft, line: C.yellow, titleColor: C.yellow, titleSize: 22, bodySize: 18, align: "center" });
  addStageNode(slide, 882, 180, 328, 156, "OVERDUE", "The deadline passed before recovery.", { fill: C.redSoft, line: C.red, titleColor: C.red, titleSize: 22, bodySize: 18, align: "center" });

  addText(slide, "The state becomes a cost only when the outcome is known:", 82, 382, 900, 34, { fontSize: 21, bold: true, color: C.gray800 });
  addStageNode(slide, 70, 430, 350, 126, "Recovered within 79 steps", "STL cost = 0", { fill: C.greenSoft, line: C.green, titleColor: C.green, titleSize: 19, bodySize: 19, align: "center" });
  addStageNode(slide, 465, 430, 350, 126, "Deadline missed", "STL cost = 1", { fill: C.redSoft, line: C.red, titleColor: C.red, titleSize: 19, bodySize: 19, align: "center" });
  addStageNode(slide, 860, 430, 350, 126, "Episode ends while pending", "terminal unresolved -> cost = 1", { fill: C.purpleSoft, line: C.purple, titleColor: C.purple, titleSize: 19, bodySize: 17, align: "center" });

  addText(slide, "This numerical cost is the signal that Safe RL can optimize.", 258, 596, 764, 38, { fontSize: 23, bold: true, color: C.orangeDark, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/docs/stage1_rule_monitor_spec.md",
    "/Users/yuhang/Downloads/STL/src/safety_stl/monitor.py",
  ]);
}

// Slide 8
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "Rule and Monitor Checks Are Complete", 8);

  addLabel(slide, "COMPLETED", 84, 116, 150, C.green, C.greenSoft);
  addText(slide, "Three independent checks agree on the declared cases:", 84, 166, 820, 34, { fontSize: 22, bold: true, color: C.gray800 });
  addStageNode(slide, 70, 216, 350, 126, "Online monitor", "Runs causally during the episode.", { fill: C.greenSoft, line: C.green, titleColor: C.green, titleSize: 21, bodySize: 17 });
  addStageNode(slide, 465, 216, 350, 126, "Direct offline oracle", "Re-evaluates the saved trajectory independently.", { fill: C.blueSoft, line: C.blue, titleColor: C.blue, titleSize: 21, bodySize: 17 });
  addStageNode(slide, 860, 216, 350, 126, "RTAMT reference", "Provides an external STL semantics check.", { fill: C.purpleSoft, line: C.purple, titleColor: C.purple, titleSize: 21, bodySize: 17 });

  addRect(slide, 70, 388, 500, 178, { fill: C.gray50, line: C.gray200, lineWidth: 1 });
  addText(slide, "Why K = 79", 102, 414, 220, 34, { fontSize: 22, bold: true, color: C.orangeDark });
  addText(slide, "95th percentile = 63 steps\n63 x 1.25 = 78.75\nceil(78.75) = 79 steps", 112, 462, 390, 86, { fontSize: 21, bold: true, color: C.black });

  addRect(slide, 610, 388, 600, 178, { fill: C.orangeSoft, line: C.orange, lineWidth: 1.5 });
  addText(slide, "What the completed work proves", 642, 414, 500, 34, { fontSize: 22, bold: true, color: C.orangeDark });
  addText(slide, "- 79 steps is evidence-based and generally achievable here.\n- Environment, distance signal, monitor, cost, visualization, and logs run together.", 650, 462, 510, 88, { fontSize: 18, color: C.black });
  addText(slide, "It does not yet prove that a trained Safe RL policy will reduce violations.", 244, 586, 792, 58, { fontSize: 21, bold: true, color: C.red, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/docs/rule_calibration_report.md",
    "/Users/yuhang/Downloads/STL/docs/monitor_agreement_report.md",
    "/Users/yuhang/Downloads/STL/docs/visualization.md",
  ]);
}

// Slide 9
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addTitle(slide, "Next: Build the OmniSafe Wrapper", 9);

  addText(slide, "The wrapper connects the tested STL cost to Safe RL without changing the benchmark task.", 82, 116, 1070, 42, { fontSize: 23, bold: true, color: C.orangeDark });
  addArrow(slide, 418, 286, 64, 32, C.orange);
  addArrow(slide, 798, 286, 64, 32, C.orange);
  addStageNode(slide, 70, 202, 348, 190, "Environment step", "Keep the task reward, native hazard cost, distance signal, and monitor state separate.", { fill: C.blueSoft, line: C.blue, titleColor: C.blue, titleSize: 22, bodySize: 18 });
  addStageNode(slide, 482, 202, 316, 190, "OmniSafe wrapper", "Expose the selected safety cost in the format expected by the Safe RL algorithm.", { fill: C.orangeSoft, line: C.orange, lineWidth: 3, titleColor: C.orangeDark, titleSize: 22, bodySize: 18 });
  addStageNode(slide, 862, 202, 348, 190, "First integration test", "Run a short update and verify that OmniSafe receives the intended STL cost.", { fill: C.greenSoft, line: C.green, titleColor: C.green, titleSize: 22, bodySize: 18 });

  addText(slide, "After the wrapper passes, train three matched agents:", 82, 446, 760, 34, { fontSize: 22, bold: true, color: C.gray800 });
  addLabel(slide, "TASK ONLY", 94, 506, 300, C.gray600, C.gray100);
  addLabel(slide, "NATIVE HAZARD COST", 490, 506, 300, C.blue, C.blueSoft);
  addLabel(slide, "STL COST", 886, 506, 300, C.orangeDark, C.orangeSoft);
  addText(slide, "Compare goal-reaching performance and temporal safety violations.", 220, 584, 840, 42, { fontSize: 23, bold: true, color: C.black, align: "center" });
  addFooter(slide, "Language-Grounded STL Safe RL | Current next step: OmniSafe wrapper");
  addNotes(slide, [
    "/Users/yuhang/Downloads/STL/docs/CURRENT_STAGE1_STATUS.md",
    "/Users/yuhang/Downloads/STL/docs/stage1_plan.md",
    "/Users/yuhang/Downloads/STL/AGENTS.md",
  ]);
}

await fs.mkdir(OUT_DIR, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${OUT_DIR}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
  await fs.writeFile(`${OUT_DIR}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text());
}
await writeBlob(`${OUT_DIR}/deck-montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(FINAL_PPTX);
