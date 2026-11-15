"""Current-design README, complete technical answers, module catalog and evaluation."""
import csv
import json
import re
from pathlib import Path
from statistics import mean,median
from .evidence import load

NETWORK=[('C1','Convolution + tanh','6 x 28 x 28','6x1x5x5',156,117600,1570),
         ('S2','Average pool + tanh','6 x 14 x 14','2x2 / stride 2',0,0,0),
         ('C3','Convolution + tanh','16 x 10 x 10','16x6x5x5',2416,240000,2400),
         ('S4','Average pool + tanh','16 x 5 x 5','2x2 / stride 2',0,0,0),
         ('C5','Convolution + tanh','120 x 1 x 1','120x16x5x5',48120,48000,1920),
         ('F6','Dense + tanh','84','84x120',10164,10080,408),
         ('F7','Dense + softmax','10','10x84',850,840,34)]

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])

def catalog(root):
    root=Path(root);entries=[]
    roles={'pe_ws':'Stationary weight, east activation, south partial sum','pe_os':'Local output accumulation with east A/south B','pe_is':'Stationary activation, south weight, east partial sum',
      'sa_ws_5x5':'5x5 WS grid and bottom-edge result gathering','sa_os_5x5':'5x5 OS grid and parallel accumulator capture','sa_is_5x5':'5x5 IS grid and right-edge result gathering',
      'sa_tile_engine':'Static dataflow selection at elaboration','dram_model':'Four-cycle held-response weight memory','weight_cache':'1 KiB direct-mapped SRAM with chained L2 line refill','weight_memory':'Direct/cached memory specialization',
      'activation_memory':'Two synchronous activation/output banks','bias_rom':'236 signed Q24 biases','tanh_lut':'Overflow-safe Q24 to Q12 activation lookup','average_pool':'Exact four-input mean in Q24 before tanh',
      'pixel_frontend':'u8 normalization and 28x28-to-32x32 address mapping','layer_config':'Seven fixed layer descriptors','patch_address':'On-demand convolution/dense activation address','pool_address':'Four addresses per pooled output',
      'tile_accumulator':'25 biased 48-bit accumulators across reduction tiles','fraction_divider':'Sixteen-step restoring Q16 probability divider','argmax_serial':'Negative-safe signed comparison and first-index ties',
      'softmax10':'Maximum, exp table, denominator, probabilities and held class','lenet_core':'Complete image ownership, layer/tile sequencing and I/O',
      'lenet_top_ws':'WS synthesis top','lenet_top_os':'OS synthesis top','lenet_top_is':'IS synthesis top'}
    def close(s,start):
        depth=0
        for i in range(start,len(s)):
            if s[i]=='(':depth+=1
            elif s[i]==')':
                depth-=1
                if depth==0:return i
        raise ValueError('Unbalanced RTL header')
    for path in sorted((root/'hardware/rtl').glob('*.v')):
        s=path.read_text();name=path.stem;match=re.search(r'\bmodule\s+'+name+r'\s*',s);p=match.end()
        if s[p]=='#':p=close(s,s.index('(',p))+1
        while s[p].isspace():p+=1
        header=s[p+1:close(s,p)];ports=[];direction=None;width='1';signed=False
        for part in header.split(','):
            part=part.strip();d=re.match(r'(input|output|inout)\b',part)
            if d:
                direction=d.group(1);w=re.search(r'\[[^\]]+\]',part);width=w.group(0) if w else '1';signed=bool(re.search(r'\bsigned\b',part))
            port=re.search(r'([A-Za-z_][A-Za-z_0-9]*)\s*$',part).group(1)
            ports.append({'name':port,'direction':direction,'width':width,'signed':signed})
        entries.append({'module':name,'role':roles[name],'source':str(path.relative_to(root)),'ports':ports})
    assert len(entries)==26
    return entries

def metrics(results):
    rows=[]
    for case in results['rtl']['cases']:
        if not case['name'].startswith('lenet_'):continue
        frames=case['frames'];intervals=[f['ii_cycles'] for f in frames if f['ii_cycles']]
        ii=median(intervals) if intervals else median(f['total_cycles'] for f in frames)+2
        rows.append({'dataflow':['WS','OS','IS'][case['parameters']['DATAFLOW']],'cache':case['parameters']['CACHE_ENABLE'],'samples':len(frames),'correct':sum(f['correct'] for f in frames),
            'compute_cycles':int(median(f['compute_cycles'] for f in frames)),'transaction_cycles':int(median(f['total_cycles'] for f in frames)),'ii_cycles':ii,'l2_reads':mean(f['l2_reads'] for f in frames),'requests':mean(f['requests'] for f in frames),'hits':mean(f['hits'] for f in frames),
            'projected_latency_ms_at_100MHz':median(f['compute_cycles'] for f in frames)/100000,'projected_images_s_at_100MHz':1e8/ii,'projected_input_Mbit_s_at_100MHz':6272*100/ii,'routed_images_s':None,'power_watts':None})
    return rows

def generate(root):
    root=Path(root);r=load(root);train=r['training'];q=r['quantization'];bench=r['benchmark'];hw=metrics(r);modules=catalog(root)
    network=table(['Layer','Operation','Output','Kernel/shape','Parameters','MACs','Tiles'],NETWORK)
    accuracy=table(['Implementation','Official test images','Correct','Accuracy'],[
        ['PyTorch float32',train['test']['n'],train['test']['correct'],f"{100*train['test']['accuracy']:.2f}%"],
        ['Integer Q12 reference',q['n_test'],q['correct'],f"{100*q['accuracy']:.2f}%"]])
    cycle_table=table(['Dataflow','Weight memory','Compute cycles','Frame cycles','Start interval','RTL cohort'],[
        [x['dataflow'],'1 KiB L1 + L2' if x['cache'] else 'L2 only',f"{x['compute_cycles']:,}",f"{x['transaction_cycles']:,}",f"{x['ii_cycles']:,}",f"{x['correct']}/{x['samples']}"] for x in hw])
    throughput=table(['Dataflow','Cache','Projected latency ms','Projected images/s','Input payload Mbit/s'],[
        [x['dataflow'],x['cache'],f"{x['projected_latency_ms_at_100MHz']:.5f}",f"{x['projected_images_s_at_100MHz']:.3f}",f"{x['projected_input_Mbit_s_at_100MHz']:.6f}"] for x in hw])
    direct=next(x for x in hw if x['dataflow']=='WS' and x['cache']==0);cached=next(x for x in hw if x['dataflow']=='WS' and x['cache']==1)
    gain=direct['compute_cycles']/cached['compute_cycles'];traffic=100*(1-cached['l2_reads']/direct['l2_reads'])
    model_b=bench['results']['model_only'];e2e_b=bench['results']['normalize_pad_model']
    module_table=table(['Module','Role','Source'],[[f"`{m['module']}`",m['role'],f"[{m['source']}]({m['source']})"] for m in modules])
    readme=f"""# LeNet Systolic Inference

**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)

A complete Fashion-MNIST classifier with a trained PyTorch LeNet, an integer reference,
and **three physical 5x5 systolic dataflows: WS, OS and IS**. The 26 RTL modules implement
the full network: zero padding, convolutions, average pooling, tanh, dense layers,
softmax and held prediction outputs. A **1 KiB SRAM cache** and a **four-cycle L2 memory**
provide two reproducible weight-memory configurations.

![Hardware architecture](hardware/figures/architecture.png)

## Verified results

{accuracy}

The float/integer prediction agreement is **{100*q['prediction_agreement']:.2f}%**;
{q['floating_integer_disagreements']} decisions differ despite the equal aggregate accuracy.
Weights and biases have **{sum(q['weight_bias_clips'].values())} clipping events** during export.

{cycle_table}

**RTL scope:** each of the six configurations checks the same {direct['samples']} official test images,
all 8,084 intermediate activations per image, all ten logits, all ten probabilities
and the class. The {q['n_test']:,}-image accuracy above is measured by PyTorch and the integer
reference; it is not presented as a {q['n_test']:,}-image RTL simulation result. Additional tests
exercise signed extremes, cache conflicts, memory stalls, score/prediction stalls,
busy-start rejection and reset cancellation.

There are **{len(r['generic']['cases'])} passing generic Yosys synthesis/connectivity checks**.
Vivado mapped resources, routed timing and power are **unmeasured**. A 100 MHz clock
is a constraint target, not an achieved device frequency.

## Network and numeric contract

The network is 32x32 -> C1(6) -> S2 -> C3(16) -> S4 -> C5(120) -> F6(84) -> F7(10).
All convolutions, pooling stages and F6 use tanh; F7 uses softmax. The model contains
**61,706 parameters** and performs **416,520 useful MACs per image**. Inputs are u8/255
with a two-pixel zero border. Weights and activations use signed 16-bit Q12; biases
and accumulators use signed 48-bit Q24. Probability outputs use unsigned Q16.

## Quick start

Use Python 3.12 with the included checkpoint and verified dataset files:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
jupyter lab HW3_Matin_Firoozbakht.ipynb
```

The notebook defaults to the saved checkpoint and measured evidence. Training and
RTL simulation are controlled by explicit switches. No dataset download is needed
when using the included data directory.

## Reproduce results

```bash
# Optional: train 20 epochs on 54,000 images; validate on 6,000.
python scripts/train.py --epochs 20 --threads 4
python scripts/export_evaluate.py --rtl-images 16
python scripts/benchmark_software.py --threads 1
python -m unittest discover -s tests -v
python scripts/run_verification.py --samples 16 --jobs 3
python -m pip install pyosys
python scripts/run_generic_synthesis.py
python scripts/build_report.py
python scripts/render_figures.py
```

Icarus Verilog (`iverilog`, `vvp`) is required for simulation. `IVERILOG`, `VVP` and
`IVL_BASE` support nonstandard installations. Saved evidence is checked against
source, ROM and dataset hashes. A larger RTL cohort can be generated with
`export_evaluate.py --rtl-images N`, then simulated with `run_verification.py --samples N`.

## Vivado

```bash
python scripts/run_vivado.py
python scripts/parse_vivado.py
vivado -mode gui -source hardware/scripts/open_checkpoint.tcl -tclargs ws 0 post_route
```

All six flows use `xc7a100tcsg324-1`, a 10 ns clock target and identical I/O timing
constraints by default. `FPGA_PART`, `CLOCK_PERIOD_NS`, `LENET_DATAFLOW` and
`LENET_CACHE` select an individual build. The flow implements an out-of-context IP
core and writes real checkpoints plus utilization, timing, DRC and power reports.
`LENET_SAIF` and `LENET_SAIF_SCOPE` provide activity for power estimation; otherwise
the estimate is vectorless. Board pin mapping and bitstream programming are separate.

## Documentation and files

- [Complete answers](COMPLETE_ANSWERS.md): every implementation and evaluation question.
- [Executed notebook](HW3_Matin_Firoozbakht.ipynb): software, all RTL sources, figures and measured results.
- [Hardware guide](hardware/README.md), [port catalog](hardware/module_ports.csv) and [architecture metadata](hardware/architecture.json).
- [Specification decisions](docs/SPECIFICATION.md) and original source documents in `docs/`.
- `software/`: PyTorch model/checkpoint, all trained parameters and integer inference.
- `hardware/rtl/`: 26 modules; `hardware/tb/`: arithmetic, memory, full-network and protocol tests.
- `hardware/mem/`: trained ROMs and independent per-image reference traces.
- `results/software/`: full test predictions, training, quantization and CPU timing.
- `results/hardware/`: actual simulation logs, cycle/traffic measurements and generic synthesis.
- `hardware/figures/`, `results/figures/`: editable SVG and high-resolution PNG figures.
- `data/fashion/`: official IDX/gzip files, checksums and the dataset license.

## Interfaces

Start on `start && start_ready`; transfer 784 u8 pixels on `pixel_valid && pixel_ready`.
The core clears the 32x32 input bank and inserts the zero border itself. Ten score
records transfer on `score_valid && score_ready`, followed by a held class on
`prediction_valid && prediction_ready`. Blocked payloads remain stable. Synchronous
active-high reset cancels a frame. All three static top modules expose the same ports.
"""
    (root/'README.md').write_text(readme)
    report=f"""# Complete LeNet and Systolic-Array Answers

**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)

## 1. Specification and implementation scope

The CNN layer table defines the implemented network. It includes C5, so there are
three convolution operations. C3 is densely connected. Average-pooling stages have
no trainable scale or bias and apply tanh after the arithmetic mean. The unrelated
MLP instructions in the later PDF pages are not mixed into this CNN. Full decisions
and the source PDF are in [docs/SPECIFICATION.md](docs/SPECIFICATION.md).

{network}

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

The measured run completed {train['epochs_completed']} epochs, selected epoch
{train['best_epoch']}, and recorded {train['training_seconds']:.2f} seconds for the training/final-evaluation
script. Training used {train['cpu_threads']} CPU threads and PyTorch {train['torch_version']}.
The full checkpoint, every floating-point parameter, every integer parameter,
split indices, epoch curves and test predictions are included.

{accuracy}

Accuracy is correct classifications divided by the number of test examples.
Here the float count is {train['test']['correct']}/{train['test']['n']}; the integer count is
{q['correct']}/{q['n_test']}. Class selection uses the smallest index attaining the maximum
full logit. The two systems disagree on {q['floating_integer_disagreements']} predictions,
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
The export has {sum(q['weight_bias_clips'].values())} clipped weights/biases. For every output neuron,
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
{direct['samples']} official test images, fixed before checking predictions. Each of six WS/OS/IS
and direct/cache configurations checks {direct['samples']*8084:,} intermediate values and every
logit, probability and class. The cohort's correctness must not be generalized to
a {q['n_test']:,}-image RTL accuracy claim. A command is provided to generate/simulate a larger
cohort, with per-image reference files keeping testbench memory bounded.

{cycle_table}

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

The batch-one PyTorch CPU measurement uses {bench['threads']} thread, eval mode,
inference_mode, 100 warm-up calls and 500 timed calls per mode. The CPU is
{bench['cpu']}. Model plus softmax averages **{model_b['mean_ms']:.6f} ms**;
normalization/padding plus model/softmax averages **{e2e_b['mean_ms']:.6f} ms**.
The model-only median is {model_b['median_ms']:.6f} ms and p95 is {model_b['p95_ms']:.6f} ms.
Host load and timing variability remain visible in the supplied samples.

The following hardware numbers are **projections at the 100 MHz target**, derived
from actual RTL cycles. They are not achieved-frequency or measured-board timings.

{throughput}

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

The cache accepts the same {direct['requests']:,.0f} weight requests per image. It records
{cached['hits']:,.0f} hits and {cached['l2_reads']:,.0f} L2 reads instead of {direct['l2_reads']:,.0f}, a
**{traffic:.2f}% reduction in L2 word traffic**. Compute latency changes from
{direct['compute_cycles']:,} to {cached['compute_cycles']:,} clocks: **{gain:.6f}x** at an equal clock.
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
"""
    (root/'COMPLETE_ANSWERS.md').write_text(report)
    (root/'results/evaluation.json').write_text(json.dumps({'software':train['test'],'integer':{k:q[k] for k in ['n_test','correct','accuracy','prediction_agreement','floating_integer_disagreements']},'hardware':hw,'projected_clock_MHz':100,'projection_is_not_routed_timing':True,'payload_bits_per_raw_image':6272,'cache_compute_speedup':gain,'cache_L2_traffic_reduction_percent':traffic,'rtl_evidence_current':True,'generic_evidence_current':True},indent=2))
    with (root/'hardware/module_ports.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['module','name','direction','width','signed']);writer.writeheader()
        for m in modules:
            for p in m['ports']:writer.writerow({'module':m['module'],**p})
    figures=[str(p.relative_to(root)) for p in sorted((root/'hardware/figures').glob('*.png'))]
    architecture={'model':[32,32,1],'parameters':61706,'useful_MACs':416520,'physical_array':[5,5],'tile_calls':6332,'array_call_cycles':14,'dataflow_coordinates':{'WS':['reduction k','output n'],'OS':['spatial m','output n'],'IS':['spatial m','reduction k']},'modules':modules,'figures':figures,'numeric_formats':q['fixed_point'],'weight_memory':{'L2_words':61470,'L2_word_bits':16,'L2_response_cycles':4,'L1_data_bytes':1024,'L1_lines':64,'L1_words_per_line':8,'L1_hit_cycles':1,'L1_tag_valid_bytes':64,'refill_request_interval_cycles':4}}
    (root/'hardware/architecture.json').write_text(json.dumps(architecture,indent=2))
    guide='# LeNet Hardware Guide\n\n**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)\n\n'
    guide+='The three static tops are `lenet_top_ws`, `lenet_top_os` and `lenet_top_is`. Set `CACHE_ENABLE` to 0 or 1. Every top owns and computes the complete network from raw pixels.\n\n'
    guide+=table(['Module','Role','Source'],[[m['module'],m['role'],f"[RTL](../{m['source']})"] for m in modules])+'\n\n'
    guide+='## Figures\n\n'
    for path in figures:guide+=f'![{Path(path).stem}]({path.removeprefix("hardware/")})\n\n'
    guide+='## Ports\n\nWidths are extracted from the actual RTL headers; [CSV](module_ports.csv) and [JSON](architecture.json) contain the complete catalog. All resets are synchronous active high.\n\n'
    for m in modules:guide+='### '+m['module']+'\n\n'+table(['Port','Direction','Width','Signed'],[[p['name'],p['direction'],p['width'],p['signed']] for p in m['ports']])+'\n\n'
    guide+='## Verification and physical flow\n\nSee [complete answers](../COMPLETE_ANSWERS.md) for numerical bounds, ownership, cycle/throughput definitions, actual test scope and power-analysis limits. The generic checks pass; Vivado mapped resources, routed timing, power and generated schematic views are unmeasured.\n'
    (root/'hardware/README.md').write_text(guide)
    return r,hw
