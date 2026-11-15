`timescale 1ns/1ps
// C[5,5] = A[5,5] * B[5,5]; C remains in each PE accumulator.
module sa_os_5x5(input wire clk,rst,start,input wire [399:0] a_tile,b_tile,
 output reg busy,done,output reg [1199:0] c_tile);
 reg [3:0] step;
 wire load=start&&!busy,run=busy&&(step<13);
 wire signed [15:0] ae[0:24],be[0:24];wire av[0:24],bv[0:24];
 wire signed [47:0] acc[0:24];
 genvar r,c;
 generate for(r=0;r<5;r=r+1) begin:rows
  for(c=0;c<5;c=c+1) begin:columns
   wire signed [15:0] ai,bi;wire avi,bvi;
   if(c==0) begin
    assign avi=run&&(step>=r)&&(step<r+5);
    assign ai=avi?$signed(a_tile[(r*5+step-r)*16+:16]):16'sd0;
   end else begin assign ai=ae[r*5+c-1];assign avi=av[r*5+c-1];end
   if(r==0) begin
    assign bvi=run&&(step>=c)&&(step<c+5);
    assign bi=bvi?$signed(b_tile[((step-c)*5+c)*16+:16]):16'sd0;
   end else begin assign bi=be[(r-1)*5+c];assign bvi=bv[(r-1)*5+c];end
   pe_os u_pe(.clk(clk),.rst(rst),.clear(load),.enable(run),.a_in(ai),.b_in(bi),.av_in(avi),.bv_in(bvi),
    .a_out(ae[r*5+c]),.b_out(be[r*5+c]),.av_out(av[r*5+c]),.bv_out(bv[r*5+c]),.accumulator(acc[r*5+c]));
  end
 end endgenerate
 integer i;
 always @(posedge clk) begin
  if(rst) begin busy<=0;done<=0;step<=0;c_tile<=0;end
  else begin
   done<=0;
   if(load) begin busy<=1;step<=0;c_tile<=0;end
   else if(busy) begin
    if(step==13) begin for(i=0;i<25;i=i+1)c_tile[i*48+:48]<=acc[i];busy<=0;done<=1;end
    else step<=step+1'b1;
   end
  end
 end
endmodule
