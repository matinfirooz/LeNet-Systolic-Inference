`timescale 1ns/1ps
// PE(r,c) owns A[r,c]. B moves south; partial sums move east.
module sa_is_5x5(input wire clk,rst,start,input wire [399:0] a_tile,b_tile,
 output reg busy,done,output reg [1199:0] c_tile);
 reg [3:0] step;wire load=start&&!busy,run=busy&&(step<13);
 wire signed [15:0] be[0:24];wire bv[0:24],sv[0:24];wire signed [47:0] ps[0:24];
 genvar r,c;
 generate for(r=0;r<5;r=r+1) begin:rows
  for(c=0;c<5;c=c+1) begin:columns
   wire signed [15:0] bi;wire bvi,svi;wire signed [47:0] si;
   if(r==0) begin
    assign bvi=run&&(step>=c)&&(step<c+5);
    assign bi=bvi?$signed(b_tile[(c*5+step-c)*16+:16]):16'sd0;
   end else begin assign bi=be[(r-1)*5+c];assign bvi=bv[(r-1)*5+c];end
   if(c==0) begin assign si=48'sd0;assign svi=bvi;end
   else begin assign si=ps[r*5+c-1];assign svi=sv[r*5+c-1];end
   pe_is u_pe(.clk(clk),.rst(rst),.load(load),.enable(run),.activation_in(a_tile[(r*5+c)*16+:16]),
    .b_in(bi),.bv_in(bvi),.sv_in(svi),.sum_in(si),.b_out(be[r*5+c]),.bv_out(bv[r*5+c]),.sv_out(sv[r*5+c]),.sum_out(ps[r*5+c]));
  end
 end endgenerate
 integer m,n;
 always @(posedge clk) begin
  if(rst) begin busy<=0;done<=0;step<=0;c_tile<=0;end
  else begin
   done<=0;
   if(load) begin busy<=1;step<=0;c_tile<=0;end
   else if(busy) begin
    for(m=0;m<5;m=m+1) begin
     n=$signed({1'b0,step})-5-m;
     if(n>=0&&n<5&&sv[m*5+4]) c_tile[(m*5+n)*48+:48]<=ps[m*5+4];
    end
    if(step==13) begin busy<=0;done<=1;end else step<=step+1'b1;
   end
  end
 end
endmodule
