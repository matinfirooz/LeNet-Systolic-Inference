`timescale 1ns/1ps
module tb_lenet;
 parameter integer DATAFLOW=0,CACHE_ENABLE=0,STALLS=0,MAX_IMAGES=16,RESET_TEST=0;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,start=0,pixel_valid=0;reg[7:0]pixel=0;
 wire start_ready,busy,pixel_ready,score_valid,prediction_valid;
 reg score_ready=1,prediction_ready=1;
 wire[3:0]score_index,prediction;wire[15:0]probability;wire signed[47:0]logit;
 wire trace_valid,trace_logit_valid;wire[2:0]trace_layer;wire[12:0]trace_address;wire signed[15:0]trace_value;
 wire[31:0]cycles,tile_count,weight_requests,cache_hits,l2_reads;
 lenet_core #(.DATAFLOW(DATAFLOW),.CACHE_ENABLE(CACHE_ENABLE))dut(
  clk,rst,start,start_ready,busy,pixel_valid,pixel,pixel_ready,score_valid,score_ready,score_index,probability,logit,
  prediction_valid,prediction_ready,prediction,trace_valid,trace_layer,trace_address,trace_value,trace_logit_valid,
  cycles,tile_count,weight_requests,cache_hits,l2_reads);
 reg[15:0]gold_trace[0:8083],gold_prob[0:9];reg[47:0]gold_logit[0:9];reg[7:0]gold_pred[0:MAX_IMAGES-1];
 integer offsets[0:5];integer slot=0,checking=0,traces=0,scores=0,correct=0;
 integer n=16,fd,labels_fd,rc,p,label,rawbyte,global_cycle=0,start_cycle,last_pixel_cycle;
 integer requests_before,hits_before,reads_before;
 integer previous_start=-1,initiation_interval=0;
 reg stalled_score=0,stalled_prediction=0;reg[67:0]held_score;reg[3:0]held_prediction;
 always @(posedge clk)begin
  global_cycle=global_cycle+1;
  if(!rst&&checking)begin
   if(stalled_score&&(!score_valid||{score_index,probability,logit}!==held_score))$fatal(1,"blocked score changed");
   if(stalled_prediction&&(!prediction_valid||prediction!==held_prediction))$fatal(1,"blocked prediction changed");
   stalled_score=score_valid&&!score_ready;held_score={score_index,probability,logit};
   stalled_prediction=prediction_valid&&!prediction_ready;held_prediction=prediction;
   if(trace_valid)begin
    if(trace_layer>5)$fatal(1,"invalid trace layer");
    if(trace_value!==gold_trace[offsets[trace_layer]+trace_address])
     $fatal(1,"activation mismatch frame=%0d layer=%0d address=%0d expected=%0d got=%0d",slot,trace_layer,trace_address,$signed(gold_trace[offsets[trace_layer]+trace_address]),trace_value);
    traces=traces+1;
   end
   if(score_valid&&score_ready)begin
    if(score_index!==scores||logit!==gold_logit[scores]||probability!==gold_prob[scores])
     $fatal(1,"score mismatch frame=%0d index=%0d expected-logit=%0d got=%0d expected-prob=%0d got=%0d",slot,score_index,$signed(gold_logit[scores]),logit,gold_prob[scores],probability);
    scores=scores+1;
   end
  end
 end
 always @(negedge clk)if(STALLS&&checking)score_ready=(global_cycle%19<8);
 initial begin
  offsets[0]=0;offsets[1]=4704;offsets[2]=5880;offsets[3]=7480;offsets[4]=7880;offsets[5]=8000;
  $readmemh("hardware/mem/reference_predictions.hex",gold_pred);
  rc=$value$plusargs("N=%d",n);if(n<1||n>MAX_IMAGES)$fatal(1,"N exceeds generated reference vectors");
  fd=$fopen("data/fashion/t10k-images-idx3-ubyte","rb");labels_fd=$fopen("data/fashion/t10k-labels-idx1-ubyte","rb");
  if(!fd||!labels_fd)$fatal(1,"IDX dataset missing");
  repeat(4)@(negedge clk);rst=0;
  if(RESET_TEST)begin
   // Cancel partial input and a running convolution before the checked restart.
   start=1;@(negedge clk);start=0;while(!pixel_ready)@(negedge clk);
   repeat(40)begin pixel_valid=1;pixel=8'd127;@(negedge clk);end
   pixel_valid=0;rst=1;repeat(3)@(negedge clk);rst=0;#1;
   if(busy||score_valid||prediction_valid||!start_ready)$fatal(1,"partial-input reset failed");
   start=1;@(negedge clk);start=0;while(!pixel_ready)@(negedge clk);
   repeat(784)begin pixel_valid=1;pixel=8'd127;@(negedge clk);end
   pixel_valid=0;repeat(2000)@(negedge clk);rst=1;repeat(3)@(negedge clk);rst=0;#1;
   if(busy||score_valid||prediction_valid||!start_ready)$fatal(1,"compute reset failed");
   $display("PASS reset_aborts phases=partial_input,convolution");
  end
  for(slot=0;slot<n;slot=slot+1)begin
   $readmemh($sformatf("hardware/mem/reference/trace_%05d.hex",slot),gold_trace);
   $readmemh($sformatf("hardware/mem/reference/logits_%05d.hex",slot),gold_logit);
   $readmemh($sformatf("hardware/mem/reference/probabilities_%05d.hex",slot),gold_prob);
   while(!start_ready)@(negedge clk);
   checking=1;traces=0;scores=0;stalled_score=0;stalled_prediction=0;
   requests_before=weight_requests;hits_before=cache_hits;reads_before=l2_reads;
   start=1;@(negedge clk);start=0;start_cycle=global_cycle;
   initiation_interval=(previous_start<0)?0:start_cycle-previous_start;previous_start=start_cycle;
   rc=$fseek(fd,16+slot*784,0);rc=$fseek(labels_fd,8+slot,0);label=$fgetc(labels_fd);
   for(p=0;p<784;p=p+1)begin
    while(!pixel_ready)@(negedge clk);
    if(STALLS&&(p%17==0))begin pixel_valid=0;@(negedge clk);end
    rawbyte=$fgetc(fd);if(rawbyte<0)$fatal(1,"unexpected IDX EOF");pixel=rawbyte;pixel_valid=1;@(negedge clk);
   end
   pixel_valid=0;last_pixel_cycle=global_cycle;
   if(slot==0)begin start=1;@(negedge clk);start=0;end
   if(STALLS)prediction_ready=0;
   while(!prediction_valid)begin @(negedge clk);if(global_cycle-start_cycle>3000000)$fatal(1,"network timeout state=%0d layer=%0d",dut.state,dut.layer);end
   if(STALLS)begin repeat(23)@(negedge clk);prediction_ready=1;end
   @(posedge clk);#1;
   if(prediction!==gold_pred[slot][3:0])$fatal(1,"class mismatch");
   if(prediction==label)correct=correct+1;
   if(traces!=8084||scores!=10||tile_count!=6332)$fatal(1,"coverage counts traces=%0d scores=%0d tiles=%0d",traces,scores,tile_count);
   $display("FRAME mode=%0d cache=%0d stalls=%0d index=%0d label=%0d prediction=%0d correct=%0d total_cycles=%0d compute_cycles=%0d ii_cycles=%0d tiles=%0d requests=%0d hits=%0d l2_reads=%0d traces=%0d scores=%0d",DATAFLOW,CACHE_ENABLE,STALLS,slot,label,prediction,prediction==label,global_cycle-start_cycle,global_cycle-last_pixel_cycle,initiation_interval,tile_count,weight_requests-requests_before,cache_hits-hits_before,l2_reads-reads_before,traces,scores);
   checking=0;@(negedge clk);
  end
  $display("PASS full_network mode=%0d cache=%0d stalls=%0d samples=%0d correct=%0d intermediate_checks=%0d",DATAFLOW,CACHE_ENABLE,STALLS,n,correct,n*8084);
  $fclose(fd);$fclose(labels_fd);$finish;
 end
endmodule
