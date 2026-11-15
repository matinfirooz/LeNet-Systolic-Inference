# Implemented specification

**Matin Firoozbakht** | [@matinfirooz](https://github.com/matinfirooz)

The LeNet layer table and CNN/dataflow requirements on pages 1-4 of
[the provided PDF](HW3_on-campus.pdf) define this implementation. The supplied
[README](provided_README.md) describes the same Fashion-MNIST CNN task.

The later PDF pages contain MLP/NIST/ReLU/sigmoid instructions that conflict with
the CNN task. Those pages are treated as an unrelated appendix. The layer table
includes C5, so this implementation has three convolution operations, including
the 5x5-to-1x1 C5 layer, even though the introductory prose counts two.

| Item | Implemented choice |
| --- | --- |
| Input | Fashion-MNIST u8 pixels, divide by 255, then two zero pixels on each border |
| Layers | C1, S2, C3, S4, C5, F6, F7 with the exact tabulated dimensions |
| Convolutions | Dense connections, valid 5x5 kernels and stride 1 |
| Pooling | Parameter-free 2x2 arithmetic mean, stride 2, followed by tanh |
| Activations | tanh after C1, S2, C3, S4, C5 and F6; softmax after F7 |
| Training loss | Cross-entropy of raw logits; softmax is evaluated for inference |
| Parameters | 61,706 = 61,470 weights + 236 biases; no learned pooling coefficients |
| Array | 25 physical PEs, each containing one signed multiplier and accumulation path |
| Dataflows | Three different PE/network implementations: WS, OS and IS |
| Convolution mapping | Channel-major im2col addressing without materializing the im2col matrix in memory |
| Fixed point | Signed 16-bit Q12 weights/activations; signed 48-bit Q24 accumulators/biases |
| Slow weights | Four-clock request-to-response L2 model |
| Bonus memory | 512x16-bit SRAM data, 64 lines of eight words; one-clock hit; metadata separate |
| Activation memory | Two independent 8,192-word banks, 16 bits per word |
| Evaluation | Full 10,000-image software/integer tests and an explicitly scoped 16-image RTL cohort |
| Physical flow | Six Vivado out-of-context core flows, identical device/clock/I/O constraints |

The 5x5 PE grid is a matrix-product tile, not a constraint that the full reduction
length is five. Reduction lengths 25/150/400/120/84 are folded over multiple tiles.
All inputs, output-channel tails and reduction tails are masked explicitly.

The source package does not include the separate official report template or a
student number. The technical answers and notebook provide the content; use the
required institutional template if a formal submission needs one.
