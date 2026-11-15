`timescale 1ns/1ps
module layer_config(input wire[2:0]layer,output reg pooling,output reg[15:0]positions,channels,reduction,weight_base,
 output reg[7:0]bias_base,output reg[12:0]output_words);
 always @*begin
  pooling=0;positions=0;channels=0;reduction=0;weight_base=0;bias_base=0;output_words=0;
  case(layer)
   0:begin positions=784;channels=6;reduction=25;weight_base=0;bias_base=0;output_words=4704;end
   1:begin pooling=1;positions=196;channels=6;output_words=1176;end
   2:begin positions=100;channels=16;reduction=150;weight_base=150;bias_base=6;output_words=1600;end
   3:begin pooling=1;positions=25;channels=16;output_words=400;end
   4:begin positions=1;channels=120;reduction=400;weight_base=2550;bias_base=22;output_words=120;end
   5:begin positions=1;channels=84;reduction=120;weight_base=50550;bias_base=142;output_words=84;end
   6:begin positions=1;channels=10;reduction=84;weight_base=60630;bias_base=226;output_words=10;end
   default:begin end
  endcase
 end
endmodule
