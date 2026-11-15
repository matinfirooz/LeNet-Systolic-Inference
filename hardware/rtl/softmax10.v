`timescale 1ns/1ps
module softmax10 #(parameter EXP_FILE="hardware/mem/exp.hex")(
 input wire clk,rst,start,input wire[479:0]logits,output wire busy,output reg done,
 output wire score_valid,input wire score_ready,output wire[3:0]score_index,
 output reg[15:0]probability,output wire signed[47:0]score_logit,
 output wire prediction_valid,input wire prediction_ready,output wire[3:0]prediction);
 localparam IDLE=0,MAXIMUM=1,EXP_REQ=2,EXP_WAIT=3,DIV_START=4,DIV_WAIT=5,EMIT=6,PRED=7;
 reg[2:0]state;reg[3:0]index;
 wire signed[47:0]current_logit=$signed(logits[index*48+:48]);
 wire signed[47:0]maximum;wire[3:0]best_index;
 argmax_serial u_argmax(clk,rst,(state==IDLE)&&start,(state==MAXIMUM),index,current_logit,best_index,maximum);
 (* rom_style="block" *)reg[31:0]exp_rom[0:4096];
 reg[31:0]exp_value,exps[0:9],denominator;
 wire signed[49:0]difference=$signed({{2{maximum[47]}},maximum})-$signed({{2{current_logit[47]}},current_logit});
 wire signed[49:0]rounded=(difference+50'sd32768)>>>16;
 wire[12:0]address=(rounded>4096)?13'd4096:((rounded<0)?13'd0:rounded[12:0]);
 initial $readmemh(EXP_FILE,exp_rom);
 always @(posedge clk)if(state==EXP_REQ)exp_value<=exp_rom[address];
 wire dbusy,ddone;wire[15:0]dq;
 fraction_divider u_divider(clk,rst,(state==DIV_START),exps[index],denominator,dbusy,ddone,dq);
 assign busy=(state!=IDLE);assign score_valid=(state==EMIT);assign score_index=index;
 assign score_logit=current_logit;assign prediction_valid=(state==PRED);assign prediction=best_index;
 integer i;
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;index<=0;denominator<=0;probability<=0;done<=0;for(i=0;i<10;i=i+1)exps[i]<=0;end
  else begin
   done<=0;
   case(state)
    IDLE:if(start)begin index<=0;denominator<=0;state<=MAXIMUM;end
    MAXIMUM:if(index==9)begin index<=0;state<=EXP_REQ;end else index<=index+1'b1;
    EXP_REQ:state<=EXP_WAIT;
    EXP_WAIT:begin
     exps[index]<=exp_value;denominator<=denominator+exp_value;
     if(index==9)begin index<=0;state<=DIV_START;end else begin index<=index+1'b1;state<=EXP_REQ;end
    end
    DIV_START:state<=DIV_WAIT;
    DIV_WAIT:if(ddone)begin probability<=dq;state<=EMIT;end
    EMIT:if(score_ready)begin if(index==9)state<=PRED;else begin index<=index+1'b1;state<=DIV_START;end end
    PRED:if(prediction_ready)begin done<=1;state<=IDLE;end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
