`timescale 1ns/1ps
// PE(r,c) owns B[r,c]. A moves east; partial sums move south.
module sa_ws_5x5(input wire clk,rst,start,input wire [399:0] a_tile,b_tile,
 output reg busy,done,output reg [1199:0] c_tile);
 reg [3:0] step;wire load=start&&!busy,run=busy&&(step<13);
 wire signed [15:0] ae[0:24];wire av[0:24],sv[0:24];wire signed [47:0] ps[0:24];
 genvar r,c;
 generate for(r=0;r<5;r=r+1) begin:rows
  for(c=0;c<5;c=c+1) begin:columns
   wire signed [15:0] ai;wire avi,svi;wire signed [47:0] si;
   if(c==0) begin
    assign avi=run&&(step>=r)&&(step<r+5);
    assign ai=avi?$signed(a_tile[((step-r)*5+r)*16+:16]):16'sd0;
   end else begin assign ai=ae[r*5+c-1];assign avi=av[r*5+c-1];end
   if(r==0) begin assign si=48'sd0;assign svi=avi;end
   else begin assign si=ps[(r-1)*5+c];assign svi=sv[(r-1)*5+c];end
   pe_ws u_pe(.clk(clk),.rst(rst),.load(load),.enable(run),.weight_in(b_tile[(r*5+c)*16+:16]),
    .a_in(ai),.av_in(avi),.sv_in(svi),.sum_in(si),.a_out(ae[r*5+c]),.av_out(av[r*5+c]),.sv_out(sv[r*5+c]),.sum_out(ps[r*5+c]));
  end
 end endgenerate
 integer n,m;
 always @(posedge clk) begin
  if(rst) begin busy<=0;done<=0;step<=0;c_tile<=0;end
  else begin
   done<=0;
   if(load) begin busy<=1;step<=0;c_tile<=0;end
   else if(busy) begin
    for(n=0;n<5;n=n+1) begin
     m=$signed({1'b0,step})-5-n;
     if(m>=0&&m<5&&sv[20+n]) c_tile[(m*5+n)*48+:48]<=ps[20+n];
    end
    if(step==13) begin busy<=0;done<=1;end else step<=step+1'b1;
   end
  end
 end
endmodule
