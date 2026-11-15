`timescale 1ns/1ps
module tb_softmax;
 reg clk=0;always #5 clk=~clk;reg rst=1,start=0,ready=0,pready=0;
 reg[479:0]logits=0;wire busy,done,valid,pvalid;wire[3:0]index,pred;wire[15:0]prob;wire signed[47:0]logit;
 softmax10 dut(clk,rst,start,logits,busy,done,valid,ready,index,prob,logit,pvalid,pready,pred);
 reg[47:0]gold_logits[0:199];reg[15:0]gold_prob[0:199];reg[7:0]gold_pred[0:19];
 integer trial,i,seen,tick=0,sum;reg stalled=0,block_all=0;reg[67:0]held;
 always @(posedge clk)begin
  tick=tick+1;
  if(!rst)begin
   if(stalled&&(!valid||{index,prob,logit}!==held))$fatal(1,"softmax blocked score changed");
   stalled=valid&&!ready;held={index,prob,logit};
   if(valid&&ready)begin
    if(index!==seen||prob!==gold_prob[trial*10+seen]||logit!==gold_logits[trial*10+seen])$fatal(1,"softmax score mismatch trial=%0d i=%0d",trial,seen);
    sum=sum+prob;seen=seen+1;
   end
  end
 end
 always @(negedge clk)ready=!block_all&&(tick%13<5);
 initial begin
  $readmemh("hardware/mem/unit_softmax_logits.hex",gold_logits);$readmemh("hardware/mem/unit_softmax_probabilities.hex",gold_prob);$readmemh("hardware/mem/unit_softmax_predictions.hex",gold_pred);
  trial=0;seen=0;sum=0;repeat(4)@(negedge clk);rst=0;
  for(trial=0;trial<20;trial=trial+1)begin
   for(i=0;i<10;i=i+1)logits[i*48+:48]=gold_logits[trial*10+i];
   seen=0;sum=0;start=1;@(negedge clk);start=0;
   while(!pvalid)@(negedge clk);
   if(pred!==gold_pred[trial][3:0]||seen!=10||sum>65536||sum<65526)$fatal(1,"softmax class or probability sum failed");
   repeat(8)begin @(negedge clk);if(!pvalid||pred!==gold_pred[trial][3:0])$fatal(1,"class not held");end
   pready=1;@(negedge clk);pready=0;@(negedge clk);
  end
  // Reset a blocked score and a held prediction in isolated transactions.
  trial=0;seen=0;sum=0;block_all=1;
  for(i=0;i<10;i=i+1)logits[i*48+:48]=gold_logits[i];
  start=1;@(negedge clk);start=0;while(!valid)@(negedge clk);repeat(5)@(negedge clk);
  rst=1;repeat(3)@(negedge clk);rst=0;stalled=0;block_all=0;
  if(busy||valid||pvalid)$fatal(1,"softmax reset failed");
  seen=0;sum=0;start=1;@(negedge clk);start=0;while(!pvalid)@(negedge clk);repeat(5)@(negedge clk);
  rst=1;repeat(3)@(negedge clk);rst=0;stalled=0;
  if(busy||valid||pvalid)$fatal(1,"held-prediction reset failed");
  $display("PASS softmax: 20 distributions, negative logits/ties/extremes, lossless score stalls, held predictions and reset");$finish;
 end
endmodule
