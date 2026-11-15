`timescale 1ns/1ps
module tb_arrays;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,start=0;reg[399:0]a,b;wire[1199:0]c0,c1,c2;wire[2:0]busy,done;
 sa_ws_5x5 ws(clk,rst,start,a,b,busy[0],done[0],c0);
 sa_os_5x5 os(clk,rst,start,a,b,busy[1],done[1],c1);
 sa_is_5x5 ins(clk,rst,start,a,b,busy[2],done[2],c2);
 integer trial,i,j,k,cycles,seed=42,random_value;longint signed expected,va,vb;
 initial begin
  a=0;b=0;repeat(3)@(negedge clk);rst=0;
  for(trial=0;trial<60;trial=trial+1)begin
   for(i=0;i<25;i=i+1)begin
    random_value=$random(seed);a[i*16+:16]=(trial==0)?16'h8000:((trial==1)?16'h7fff:random_value);
    random_value=$random(seed);b[i*16+:16]=(trial==0)?16'h8000:((trial==1)?16'h8000:random_value);
   end
   start=1;@(negedge clk);start=0;cycles=0;
   while(done!=3'b111)begin @(negedge clk);cycles=cycles+1;if(cycles>20)$fatal(1,"array timeout");end
   if(cycles!=14)$fatal(1,"latency %0d",cycles);
   for(i=0;i<5;i=i+1)for(j=0;j<5;j=j+1)begin
    expected=0;
    for(k=0;k<5;k=k+1)begin va=$signed(a[(i*5+k)*16+:16]);vb=$signed(b[(k*5+j)*16+:16]);expected=expected+va*vb;end
    if($signed(c0[(i*5+j)*48+:48])!==expected||$signed(c1[(i*5+j)*48+:48])!==expected||$signed(c2[(i*5+j)*48+:48])!==expected)
     $fatal(1,"GEMM mismatch trial=%0d m=%0d n=%0d expected=%0d WS=%0d OS=%0d IS=%0d",trial,i,j,expected,$signed(c0[(i*5+j)*48+:48]),$signed(c1[(i*5+j)*48+:48]),$signed(c2[(i*5+j)*48+:48]));
   end
   @(negedge clk);
  end
  $display("PASS arrays: 60 signed matrices x 25 outputs x 3 physically distinct dataflows; latency=14 clocks");$finish;
 end
endmodule
