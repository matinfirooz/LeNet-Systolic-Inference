# Complete LeNet and Systolic-Array Answers

**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)

## 1. Specification and implementation scope

The CNN layer table defines the implemented network. It includes C5, so there are
three convolution operations. C3 is densely connected. Average-pooling stages have
no trainable scale or bias and apply tanh after the arithmetic mean. The unrelated
MLP instructions in the later PDF pages are not mixed into this CNN. Full decisions
and the source PDF are in [docs/SPECIFICATION.md](docs/SPECIFICATION.md).

| Layer | Operation | Output | Kernel/shape | Parameters | MACs | Tiles |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | Convolution + tanh | 6 x 28 x 28 | 6x1x5x5 | 156 | 117600 | 1570 |
| S2 | Average pool + tanh | 6 x 14 x 14 | 2x2 / stride 2 | 0 | 0 | 0 |
| C3 | Convolution + tanh | 16 x 10 x 10 | 16x6x5x5 | 2416 | 240000 | 2400 |
| S4 | Average pool + tanh | 16 x 5 x 5 | 2x2 / stride 2 | 0 | 0 | 0 |
| C5 | Convolution + tanh | 120 x 1 x 1 | 120x16x5x5 | 48120 | 48000 | 1920 |
| F6 | Dense + tanh | 84 | 84x120 | 10164 | 10080 | 408 |
| F7 | Dense + softmax | 10 | 10x84 | 850 | 840 | 34 |

The total is 61,706 parameters (61,470 weights and 236 biases), 416,520 useful MACs,
and 6,332 systolic tile calls per image. The two pools generate 1,576 outputs;
8,084 intermediate activation values are stored across the six non-output stages.

## 2. Dataset, preprocessing and training

Fashion-MNIST has 60,000 official training and 10,000 official test images, each
28x28 u8. MD5 and SHA-256 records accompany the exact downloaded files. The official
training partition is split class-wise into 54,000 training and 6,000 validation
examples using seed 42. The official test set is held out from optimization and
checkpoint selection. Each class contributes 5,400 training and 600 validation images.

Input pixels are divided by 255, then padded with two zeros on each side to 32x32.
The HDL reads raw pixels from the original binary IDX test file in its testbench;
the synthesizable frontend performs the normalization and padding-address mapping.
It first clears all 1,024 input words, then writes pixel (y,x) to (y+2)*32+(x+2).

The PyTorch forward path uses tanh after C1, S2, C3, S4, C5 and F6. Training passes
raw F7 logits to cross-entropy, which supplies the stable softmax/log-loss operation.
Inference explicitly evaluates softmax. AdamW uses batch size 256, learning rate
0.001, weight decay 0.0001, and a factor-0.5 learning-rate reduction after epochs
10 and 16. Model seed is 7, shuffle seed is 42, and deterministic CPU operations
are enabled. The selected checkpoint is the minimum validation-cross-entropy epoch.

The measured run completed 20 epochs, selected epoch
20, and recorded 104.92 seconds for the training/final-evaluation
script. Training used 4 CPU threads and PyTorch 2.5.1+cpu.
The full checkpoint, every floating-point parameter, every integer parameter,
split indices, epoch curves and test predictions are included.

| Implementation | Official test images | Correct | Accuracy |
| --- | --- | --- | --- |
| PyTorch float32 | 10000 | 8884 | 88.84% |
| Integer Q12 reference | 10000 | 8884 | 88.84% |

Accuracy is correct classifications divided by the number of test examples.
Here the float count is 8884/10000; the integer count is
8884/10000. Class selection uses the smallest index attaining the maximum
full logit. The two systems disagree on 11 predictions,
so equal aggregate accuracy does not mean identical predictions.

## 3. Convolution as a folded matrix product

For output position p, output channel n and flattened reduction coordinate k,
the operation is C[p,n] = bias[n] + sum_k A[p,k]*B[k,n]. A is an addressed view of
the input patch; the design does not store a duplicated im2col matrix. B[k,n] is
the trained channel-major kernel coefficient. Each call computes a 5x5 output tile
with a five-element reduction, then adds its 25 partial sums to 48-bit tile state.
Reduction tiles continue until K is exhausted. Bias is seeded exactly once per
output tile. Missing spatial positions, output channels and final reduction lanes
are zeroed. Only valid output coordinates are committed.

The loop order is output-channel tile N, spatial tile M, then reduction tile K.
For each tile the controller loads 25 A words and 25 B words, starts the selected
physical array, waits for done, and accumulates its result. All dense layers use
the same array with M=1. Their unused spatial lanes are masked, which reduces
utilization without changing numerical results.

## 4. Three physical dataflows

| Dataflow | PE row / column | Stationary state | Horizontal movement | Vertical movement | Result location |
| --- | --- | --- | --- | --- | --- |
| WS | k / n | B[k,n] | A | 48-bit partial sum | Bottom edge, gathered by m/n |
| OS | m / n | C[m,n] | A | B | Local PE accumulator |
| IS | m / k | A[m,k] | 48-bit partial sum | B | Right edge, gathered by m/n |

WS loads 25 local weights. Row r receives A[m,r] at wave clock m+r; forwarding
adds column delay. A matching partial sum reaches the same PE from the row above.
IS loads 25 local activations. Column c receives B[c,n] at clock n+c; forwarding
adds row delay, and partial sums advance from the left. OS injects A[m,k] at k+m
and B[k,n] at k+n; each PE receives matching operands at k+m+n.

Every PE performs a signed 16x16 product, sign extends it, and uses a signed 48-bit
addition. Valid bits follow register boundaries. Each full tile performs 125 useful
MACs over 13 wave clocks, plus one capture clock: **14 clocks per array call**, as
checked by the independent matrix-product testbench. The 6,332 calls therefore
contain 88,648 array-service clocks. Fill/drain, tails and dense M=1 tiles explain
why 25 multipliers do not imply 25 useful network MACs on every system clock.

All three designs deliberately share the same tile size and external schedule.
Their measured cycle counts therefore match under the same memory configuration.
Stationarity changes local storage, routing and switching activity; it does not
automatically establish a throughput or energy winner.

## 5. Numeric formats and nonlinear operations

| Quantity | Representation | Interpretation |
| --- | --- | --- |
| Raw pixel | u8 | Integer 0..255 |
| Normalized input | signed 16-bit Q12 | floor((pixel*4096+127)/255) |
| Weight / tanh output | signed 16-bit Q12 | Integer / 4096 |
| Raw product | signed 32-bit Q24 | Sign-extended before addition |
| Bias / accumulator / logit | signed 48-bit Q24 | Integer / 16777216 |
| Probability | unsigned 16-bit Q16 | Integer / 65536 |

Weights round with floor(real*4096+0.5); biases use floor(real*2^24+0.5).
The export has 0 clipped weights/biases. For every output neuron,
abs(bias) + 4096*sum(abs(weights)) bounds its accumulator because normalized inputs
and all tanh activations have magnitude at most 4096. Every recorded bound is below
2^47, so 48-bit accumulation is safe over the entire stated input domain.

The tanh ROM has 4,097 Q12 words for inputs -8..8 on a 1/256 grid. Its address is
clamp((sign_extend_49(acc)+32768) arithmetic_shift_right 16, -2048, 2048)+2048.
Widening precedes rounding, including at signed 48-bit extremes. Average pooling
sums four sign-extended Q12 words and shifts that sum left by 10 to represent the
exact mean in Q24 before the same tanh lookup; no intermediate divide rounding occurs.

Softmax first finds the signed maximum and deterministic argmax. A 4,097-entry
Q24 exponential ROM approximates exp(-delta), delta in [0,16] on a 1/256 grid.
Maximum subtraction is widened to 50 bits before rounding. Ten exp values sum in
32 bits. A sixteen-step restoring divider emits floor((exp*65536)/denominator).
The integer probabilities sum to at most 65,536 and lose fewer than ten integer
units to final division truncation; lookup approximation adds its own error relative
to real softmax. Predictions use the full logits, so probability quantization does
not manufacture class ties.

## 6. Memory hierarchy, ownership and interfaces

L2 contains 61,470 16-bit weight words: 122,940 bytes. The separate 236x48-bit bias
ROM contains 1,416 bytes. Tanh and exp ROMs contain 8,194 and 16,388 bytes. Activations
use two 8,192x16-bit banks, 32 KiB total. A source bank is read while a separate
destination bank receives outputs; bank ownership swaps only after a complete layer.
The design never depends on unwritten padded/tail cells.

The bonus L1 data array is exactly 512x16 = 1,024 bytes. It is direct mapped with
64 lines of eight words. Each line adds a seven-bit tag and valid flag: 64 bytes
of metadata outside the data capacity. A hit responds one clock after the request
handshake. A miss fills the line from the same four-cycle L2. L2 response retirement
and the next refill request can share an edge, giving a four-clock refill initiation
interval. The final line issues only valid L2 addresses and supplies zeros for padding.

One frame owns the controller, memories and result state until the final class is
accepted. Start is accepted only on start && start_ready. Pixels, scores and predictions
use independent valid/ready handshakes. Score data/index/logit and the final class
remain stable under downstream stalls. A synchronous active-high reset cancels a
partial frame, an active convolution or a held output. Memory data are not globally
reset; complete writes and masks establish the next frame's live state.

## 7. Actual RTL verification

The official software test uses 10,000 images. The delivered RTL cohort is the first
16 official test images, fixed before checking predictions. Each of six WS/OS/IS
and direct/cache configurations checks 129,344 intermediate values and every
logit, probability and class. The cohort's correctness must not be generalized to
a 10,000-image RTL accuracy claim. A command is provided to generate/simulate a larger
cohort, with per-image reference files keeping testbench memory bounded.

| Dataflow | Weight memory | Compute cycles | Frame cycles | Start interval | RTL cohort |
| --- | --- | --- | --- | --- | --- |
| WS | L2 only | 1,101,438 | 1,103,246 | 1,103,248 | 16/16 |
| WS | 1 KiB L1 + L2 | 1,082,295 | 1,084,103 | 1,084,105 | 16/16 |
| OS | L2 only | 1,101,438 | 1,103,246 | 1,103,248 | 16/16 |
| OS | 1 KiB L1 + L2 | 1,082,295 | 1,084,103 | 1,084,105 | 16/16 |
| IS | L2 only | 1,101,438 | 1,103,246 | 1,103,248 | 16/16 |
| IS | 1 KiB L1 + L2 | 1,082,295 | 1,084,103 | 1,084,105 | 16/16 |

Additional regressions include 60 signed matrix pairs across all three physical
arrays, 1,000 divider cases, 128 tanh/pool cases, 20 softmax distributions with ties,
negative logits and full signed extremes, 126 memory reads per memory mode plus
an interrupted miss, and a complete restarted/stalled inference. Cache tests cover
conflicts, held responses, one-clock hits, four-clock L2 responses and final-line bounds.
Protocol tests cover partial-input/convolution reset cancellation, softmax reset,
score stalls, held predictions and a start pulse while busy. Actual logs and hashes
are in results/hardware/verification.json; no software cycle model is substituted
for these HDL executions.

Generic Yosys checks cover all three array cores and all six complete top-level
specializations. Each retains 25 signed 16x16 PE multipliers, with no inferred latches
and passing hierarchy/connectivity checks. These are generic synthesis results,
not device-specific LUT/DSP/BRAM counts or routed timing.

## 8. Evaluation 1: speed and fairness

**How is hardware inference time calculated?** Count clocks between explicitly
defined handshake events. Compute latency here runs from the final accepted pixel
to final class retirement. Full-frame latency includes input-bank clear and pixel
loading. If the verified operating period is T_ns, latency_ms = cycles*T_ns/1,000,000.
Simulator wall-clock time is verification cost and is not hardware inference latency.

The batch-one PyTorch CPU measurement uses 1 thread, eval mode,
inference_mode, 100 warm-up calls and 500 timed calls per mode. The CPU is
AMD EPYC 9V74 80-Core Processor. Model plus softmax averages **0.351928 ms**;
normalization/padding plus model/softmax averages **0.422177 ms**.
The model-only median is 0.288385 ms and p95 is 0.610215 ms.
Host load and timing variability remain visible in the supplied samples.

The following hardware numbers are **projections at the 100 MHz target**, derived
from actual RTL cycles. They are not achieved-frequency or measured-board timings.

| Dataflow | Cache | Projected latency ms | Projected images/s | Input payload Mbit/s |
| --- | --- | --- | --- | --- |
| WS | 0 | 11.01438 | 90.641 | 0.568503 |
| WS | 1 | 10.82295 | 92.242 | 0.578542 |
| OS | 0 | 11.01438 | 90.641 | 0.568503 |
| OS | 1 | 10.82295 | 92.242 | 0.578542 |
| IS | 0 | 11.01438 | 90.641 | 0.568503 |
| IS | 1 | 10.82295 | 92.242 | 0.578542 |

**Why is a direct software/hardware speed ratio unfair?** The CPU executes float32
with its cache/vector implementation, while RTL uses Q12 and lookup approximations.
CPU model-only timing excludes input transfer; the full hardware transaction includes
zero-fill/loading and a single-frame controller. The L2 model specifies latency but
does not model a complete DDR controller, burst bandwidth, refresh or clock crossings.
The FPGA frequency is unverified. CPU/FPGA transfer and launch costs are also absent
from an accelerator-board end-to-end measurement. Those scopes must be reported
instead of treating the two table columns as equivalent workloads/platforms.

**How should accelerators be compared fairly?** Use the same checkpoint, acceptable
accuracy, numerical precision, dataset cohort, batch size and timing scope. Use the
same FPGA/technology, clock constraints, memory capacity, latency/bandwidth and
implementation effort. Measure achieved feasible clocks with setup/hold, clock-coverage
and DRC checks, then time identical end-to-end transfers. Report area/resources,
latency, sustained initiation interval, energy per image and accuracy together.
For dataflows in this project the array count, arithmetic, software model and external
schedule are held fixed; only stationary mapping and the explicitly labeled cache
configuration vary.

## 9. Evaluation 2: throughput and power

Throughput uses the measured **start-to-start initiation interval**, not only the
first-frame latency. This serial frame owner needs two admission/retirement clocks
beyond a no-stall frame latency. The testbench records start intervals directly.
At an actually verified frequency f, images_per_second = f / II.

One raw input image carries 28*28*8 = **6,272 payload bits**. The reported input
throughput is 6272*f/II bits/s. Counting the padded 32*32*16 internal representation
would instead use 16,384 bits/image and must be labeled as a different convention.
The ten Q16 scores plus four-bit class carry 164 output payload bits/image, so output
payload throughput is 164*f/II. Internal reuse traffic is not counted as new input bits.

Vivado is unavailable here. For each of the six configurations, device utilization,
routed setup/hold slack, feasible clock, total on-chip power and routed throughput
remain null/not_run. The provided flow performs out-of-context synthesis, placement,
routing and report/checkpoint generation with identical constraints. Power is vectorless
unless matching SAIF activity is supplied and its annotation coverage inspected.

**Which dataflow has the best throughput?** At the same feasible clock and memory
mode, the measured schedules tie. A routed frequency difference could change the
ranking, but it has not been measured. **Which is most power-efficient?** There is
no defensible measured winner without power/activity reports. Stationarity explains
different operand/partial-sum movement but is not sufficient evidence of lower total
on-chip power. Energy_per_image = total_power_watts / images_per_second; dynamic
and total power, temperature, voltage and activity assumptions must be consistent.

## 10. Bonus: measured two-level-memory effect

The cache accepts the same 130,470 weight requests per image. It records
119,189 hits and 90,246 L2 reads instead of 130,470, a
**30.83% reduction in L2 word traffic**. Compute latency changes from
1,101,438 to 1,082,295 clocks: **1.017687x** at an equal clock.
The measured improvement is limited because refill/tag/control costs, compulsory
weights and direct-mapped conflicts remain. A high hit ratio alone is not a latency
result; the report uses complete HDL transaction counts. All three dataflows have
the same cache result under their common memory request schedule.

The 1 KiB capacity is data SRAM; the separate tag/valid metadata and controller
state are explicitly accounted for. Cache, pipeline and frame state are reset-safe.
Every bonus configuration is numerically identical to its uncached integer counterpart
on the tested RTL cohort.

## 11. Reproduction and evidence limits

Install requirements, open the notebook, and use the commands in README.md. Retraining
or editing verified RTL/ROMs requires re-export and fresh simulation. The evidence
checker rejects mismatched hashes. The shipped checkpoint and full dataset permit
offline reproduction; the optional download script verifies official checksums.

The technical content is complete for the supplied requirements. Actual Vivado
implementation metrics and Vivado schematic screenshots require running the included
flow on a machine with that tool. The authored SVG/PNG diagrams document the real
RTL, and are identified as authored figures. No mapped-resource, clock-closure or
power result is invented.

## Sources

- Provided layer table and task: [HW3 source PDF](docs/HW3_on-campus.pdf).
- Official data, IDX layout, checksums and MIT license: https://github.com/zalandoresearch/fashion-mnist
- PyTorch inference mode: https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad_mode.inference_mode.html
- PyTorch reproducibility: https://docs.pytorch.org/docs/stable/notes/randomness.html
- AMD synthesis command: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/synth_design
- AMD timing summary: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_timing_summary
- AMD power and SAIF: https://docs.amd.com/r/2026.1-English/ug835-vivado-tcl-commands/report_power and https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/read_saif
