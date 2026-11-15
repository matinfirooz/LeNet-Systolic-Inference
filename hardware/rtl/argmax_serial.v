`timescale 1ns/1ps
module argmax_serial(input wire clk,rst,clear,valid,input wire[3:0]index,input wire signed[47:0]logit,
 output reg[3:0]best_index,output reg signed[47:0]best_logit);
 reg seen;
 always @(posedge clk)begin
  if(rst||clear)begin seen<=0;best_index<=0;best_logit<=0;end
  else if(valid&&(!seen||logit>best_logit||(logit==best_logit&&index<best_index)))begin
   seen<=1;best_index<=index;best_logit<=logit;
  end
 end
endmodule
