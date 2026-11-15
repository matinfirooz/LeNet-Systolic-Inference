`timescale 1ns/1ps
module tile_accumulator(input wire clk,rst,seed,accumulate,input wire[239:0]biases,
 input wire[1199:0]partial_tile,output wire[1199:0]values);
 reg signed[47:0]acc[0:24];integer i;
 genvar g;generate for(g=0;g<25;g=g+1)begin:pack assign values[g*48+:48]=acc[g];end endgenerate
 always @(posedge clk)begin
  if(rst)for(i=0;i<25;i=i+1)acc[i]<=0;
  else if(seed)for(i=0;i<25;i=i+1)acc[i]<=$signed(biases[(i%5)*48+:48]);
  else if(accumulate)for(i=0;i<25;i=i+1)acc[i]<=acc[i]+$signed(partial_tile[i*48+:48]);
 end
endmodule
