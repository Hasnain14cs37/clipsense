import type { QAResponse, VideoResult } from "../types/contracts";

/** Demo result: 3Blue1Brown — "But what is a neural network?" (aircAruvnKk).
 *  Lets the whole UI run with a real, seekable YouTube video before the
 *  backend endpoints exist. Structure matches the plan's contracts exactly. */
export const MOCK_RESULT: VideoResult = {
  video_id: "aircAruvnKk",
  title: "But what is a neural network?",
  channel: "3Blue1Brown",
  duration: 1136,
  transcript_source: "youtube-captions",
  tldr: "A neural network is layers of simple numeric units. Each neuron holds an activation between 0 and 1, and weighted connections between layers gradually turn raw pixel values into structured ideas — edges, then patterns, then digits. Learning means finding the weights and biases that make this pipeline accurate.",
  takeaways: [
    "A neuron is just a number between 0 and 1 called its activation — nothing mystical.",
    "The 28×28 pixel grid becomes a 784-neuron input layer; the output layer has one neuron per digit.",
    "Hidden layers are meant to detect intermediate structure: edges combine into loops and lines, which combine into digits.",
    "Each connection carries a weight; each neuron adds a bias before squishing the result into 0–1.",
    "One layer's activations are computed from the previous layer with a weighted sum — compactly, a matrix product.",
    "Learning = adjusting roughly 13,000 weights and biases so the network classifies examples correctly.",
  ],
  chapters: [
    {
      title: "Neurons hold numbers",
      start: 0,
      end: 218,
      summary:
        "The network is introduced with the handwritten-digit task. A neuron is defined as a unit holding an activation from 0 to 1. The 28×28 input image becomes 784 input neurons whose activations are the pixel brightness values, and the 10 output neurons represent the digits 0–9.",
      key_points: [
        "Recognizing sloppy digits is easy for brains, hard to program explicitly",
        "Neuron = a number between 0 and 1, its activation",
        "784 input neurons map one-to-one onto the image pixels",
      ],
      evidence_timestamps: [42, 128, 196],
    },
    {
      title: "Why layers might detect structure",
      start: 218,
      end: 500,
      summary:
        "The hope for hidden layers: the second layer could detect small edges, the third could combine edges into loops and long lines, and the final layer could match those parts to digits. An 8 is two loops; a 4 is three straight lines. This layered decomposition is the motivation, even if the trained network is messier.",
      key_points: [
        "Hidden layers should build up from edges to patterns to digits",
        "Loops and lines are reusable parts across many digits",
        "The same idea applies to speech: sounds to syllables to words",
      ],
      evidence_timestamps: [312, 388, 441],
    },
    {
      title: "Weights, biases and the sigmoid",
      start: 500,
      end: 870,
      summary:
        "Each connection gets a weight; a weighted sum of activations measures how well a region matches a pattern. A bias shifts when the neuron should fire, and the sigmoid squishes the result into 0–1. Counting them all, this small network has about 13,000 adjustable parameters.",
      key_points: [
        "Weighted sums detect pixel patterns such as edges in a region",
        "Bias sets the threshold before a neuron activates",
        "About 13,002 weights and biases define this network",
      ],
      evidence_timestamps: [545, 678, 792],
    },
    {
      title: "Layers as matrix multiplication",
      start: 870,
      end: 1136,
      summary:
        "All the weighted sums for one layer collapse into a single matrix–vector product plus a bias vector, passed through the sigmoid. The network is really a function with 13,000 knobs — and 'learning' means letting the computer find good settings for them, which the next video covers.",
      key_points: [
        "Layer transition = matrix product + bias, then sigmoid",
        "Matrix form is also how libraries make networks fast",
        "Learning is the search for the right weights and biases",
      ],
      evidence_timestamps: [902, 1010, 1095],
    },
  ],
  vision: [
    {
      timestamp: 42,
      frame_type: "chart",
      ocr_text: "28 x 28 = 784 pixels",
      description: "A handwritten 3 on a pixel grid, each cell showing its brightness value.",
      confidence: 0.94,
    },
    {
      timestamp: 128,
      frame_type: "slide",
      ocr_text: "activation: a number between 0.0 and 1.0",
      description: "A single neuron circle annotated with its activation value.",
      confidence: 0.91,
    },
    {
      timestamp: 312,
      frame_type: "chart",
      ocr_text: "",
      description: "The four-layer network diagram with two hidden layers of 16 neurons.",
      confidence: 0.88,
    },
    {
      timestamp: 388,
      frame_type: "slide",
      ocr_text: "8 = two loops   9 = loop + line",
      description: "Digits decomposed into loop and line components.",
      confidence: 0.9,
    },
    {
      timestamp: 545,
      frame_type: "chart",
      ocr_text: "w1a1 + w2a2 + w3a3 + ... + wnan",
      description: "Weighted sum of first-layer activations highlighted over an image region.",
      confidence: 0.93,
    },
    {
      timestamp: 678,
      frame_type: "chart",
      ocr_text: "sigma(x) = 1 / (1 + e^-x)",
      description: "The sigmoid curve squishing the number line into the 0–1 band.",
      confidence: 0.95,
    },
    {
      timestamp: 902,
      frame_type: "chart",
      ocr_text: "a(1) = sigma(W a(0) + b)",
      description: "The layer update written as one matrix equation.",
      confidence: 0.92,
    },
  ],
  critic: {
    faithfulness: 0.94,
    checked: 17,
    results: [
      {
        claim: "The network has about 13,000 adjustable weights and biases.",
        supported: true,
        evidence: "[13:12] \"...a total of 13,002 weights and biases.\"",
        confidence: 0.97,
        revision_needed: false,
      },
      {
        claim: "Hidden layers detect edges, then loops and lines, then digits.",
        supported: true,
        evidence:
          "[06:28] The hope is that the second layer picks up edges and the third recognizes loops and lines — stated as the motivating hope, not a verified property of the trained network.",
        confidence: 0.84,
        revision_needed: true,
      },
      {
        claim: "The output layer has ten neurons, one for each digit.",
        supported: true,
        evidence: "[03:16] \"...the last layer has 10 neurons, each representing one of the digits.\"",
        confidence: 0.98,
        revision_needed: false,
      },
    ],
  },
};

export const MOCK_QA: Record<string, QAResponse> = {
  default: {
    answer:
      "The sigmoid squishes any weighted sum into the 0–1 range so it can act as an activation. The video notes at [11:18] that a bias is added before the squish to control when the neuron becomes meaningfully active.",
    citations: [
      {
        timestamp: 678,
        source_type: "vision",
        excerpt: "sigma(x) = 1 / (1 + e^-x) — the sigmoid curve on screen",
      },
      {
        timestamp: 702,
        source_type: "transcript",
        excerpt: "very negative inputs end up close to zero, very positive inputs end up close to one",
      },
    ],
    confidence: 0.89,
  },
};

/** Per-stage narration lines for the mock progress feed. */
export const MOCK_STAGE_DETAIL: Record<string, string[]> = {
  ingesting: ["Checking the link", "Reading video metadata", "Preparing audio track"],
  listening: ["Captions found — 391 lines", "Merging captions into sentences"],
  watching: ["Sampling frames every 4s", "38 unique frames after dedupe", "Reading slides and formulas"],
  summarizing: ["Splitting into topic chunks", "Writing chapter notes", "Composing the final summary"],
  verifying: ["Collecting 17 claims", "Checking claims against evidence", "Revising 1 weak claim"],
};
