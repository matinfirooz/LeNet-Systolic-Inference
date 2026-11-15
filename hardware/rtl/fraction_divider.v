`timescale 1ns/1ps
// floor((numerator << 16)/denominator), 16 restoring steps; output saturates at 65535.
module fraction_divider(input wire clk,rst,start,input wire[31:0]numerator,denominator,
 output reg busy,done,output reg[15:0]quotient);
 reg[31:0]remainder,divisor;reg[4:0]iteration;
 wire[32:0]shifted={remainder,1'b0};wire take=shifted>={1'b0,divisor};
 always @(posedge clk)begin
  if(rst)begin busy<=0;done<=0;quotient<=0;remainder<=0;divisor<=0;iteration<=0;end
  else begin
   done<=0;
   if(start&&!busy)begin
    if(denominator==0)begin quotient<=0;done<=1;end
    else if(numerator>=denominator)begin quotient<=16'hffff;done<=1;end
    else begin busy<=1;remainder<=numerator;divisor<=denominator;quotient<=0;iteration<=0;end
   end else if(busy)begin
    remainder<=take?(shifted-{1'b0,divisor}):shifted;
    quotient<={quotient[14:0],take};
    if(iteration==15)begin busy<=0;done<=1;end else iteration<=iteration+1'b1;
   end
  end
 end
endmodule
