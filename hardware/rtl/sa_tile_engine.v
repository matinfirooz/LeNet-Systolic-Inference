`timescale 1ns/1ps
module sa_tile_engine #(parameter integer DATAFLOW=0)(input wire clk,rst,start,
 input wire [399:0] a_tile,b_tile,output wire busy,done,output wire [1199:0] c_tile);
 generate
  if(DATAFLOW==0) begin:WS
   sa_ws_5x5 u_array(.clk(clk),.rst(rst),.start(start),.a_tile(a_tile),.b_tile(b_tile),.busy(busy),.done(done),.c_tile(c_tile));
  end else if(DATAFLOW==1) begin:OS
   sa_os_5x5 u_array(.clk(clk),.rst(rst),.start(start),.a_tile(a_tile),.b_tile(b_tile),.busy(busy),.done(done),.c_tile(c_tile));
  end else begin:IS
   sa_is_5x5 u_array(.clk(clk),.rst(rst),.start(start),.a_tile(a_tile),.b_tile(b_tile),.busy(busy),.done(done),.c_tile(c_tile));
  end
 endgenerate
endmodule
