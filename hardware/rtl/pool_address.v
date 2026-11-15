`timescale 1ns/1ps
module pool_address(input wire[2:0]layer,input wire[12:0]output_index,input wire[1:0]element,
 output reg[12:0]address);
 always @*begin
  if(layer==1)address=(output_index/196)*784+(2*((output_index%196)/14)+element[1])*28+2*(output_index%14)+element[0];
  else address=(output_index/25)*100+(2*((output_index%25)/5)+element[1])*10+2*(output_index%5)+element[0];
 end
endmodule
