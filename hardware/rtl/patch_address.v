`timescale 1ns/1ps
module patch_address(input wire[2:0]layer,input wire[15:0]position,k_index,
 output reg[12:0]address);
 always @*case(layer)
  0:address=(position/28+k_index/5)*32+position%28+k_index%5;
  2:address=(k_index/25)*196+(position/10+(k_index%25)/5)*14+position%10+k_index%5;
  default:address=k_index;
 endcase
endmodule
