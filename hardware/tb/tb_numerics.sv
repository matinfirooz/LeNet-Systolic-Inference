`timescale 1ns/1ps
module tb_numerics;
 reg clk=0;always #5 clk=~clk;reg rst=1;
 reg divstart=0;reg[31:0]num=0,den=1;wire divbusy,divdone;wire[15:0]quotient;
 fraction_divider d(clk,rst,divstart,num,den,divbusy,divdone,quotient);
 reg lut_en=0;reg signed[47:0]acc=0;wire signed[15:0]tanh_value;
 tanh_lut lut(clk,lut_en,acc,tanh_value);
 reg signed[15:0]pa,pb,pc,pd;wire signed[47:0]mean;
 average_pool pool(pa,pb,pc,pd,mean);
 reg[15:0]tanh_gold[0:4096];integer i,seed=123,r1,r2,idx;longint unsigned expected;longint signed wide,rounded;
 initial begin
  $readmemh("hardware/mem/tanh.hex",tanh_gold);pa=0;pb=0;pc=0;pd=0;
  repeat(4)@(negedge clk);rst=0;
  for(i=0;i<1000;i=i+1)begin
   r1=$random(seed);r2=$random(seed);den={1'b0,r2[30:0]}+1;num={1'b0,r1[30:0]}%den;
   if(i==0)begin num=32'hfffffffe;den=32'hffffffff;end
   if(i==1)begin num=1;den=2;end
   if(i==2)begin num=0;den=1;end
   expected=({32'b0,num}<<16)/den;divstart=1;@(negedge clk);divstart=0;while(!divdone)@(negedge clk);
   if(quotient!==expected)$fatal(1,"divider mismatch n=%0d d=%0d expected=%0d got=%0d",num,den,expected,quotient);
   @(negedge clk);
  end
  for(i=0;i<128;i=i+1)begin
   r1=$random(seed);acc=$signed(r1)*12345;
   if(i==0)acc=48'h800000000000;if(i==1)acc=48'h7fffffffffff;
   wide=$signed(acc);rounded=(wide+32768)>>>16;
   if(rounded< -2048)idx=0;else if(rounded>2048)idx=4096;else idx=rounded+2048;
   lut_en=1;@(negedge clk);lut_en=0;
   if(tanh_value!==tanh_gold[idx])$fatal(1,"tanh saturation/rounding mismatch");
   pa=$random(seed);pb=$random(seed);pc=$random(seed);pd=$random(seed);#1;
   wide=$signed(pa);wide=wide+$signed(pb)+$signed(pc)+$signed(pd);wide=wide<<<10;
   if(mean!==wide)$fatal(1,"average-pool overflow or precision error");
  end
  $display("PASS numerics: 1000 restoring divisions; 128 widened tanh/average-pool cases including signed 48-bit extremes");$finish;
 end
endmodule
