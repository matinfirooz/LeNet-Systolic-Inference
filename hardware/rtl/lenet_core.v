`timescale 1ns/1ps
// Complete autonomous inference. Host supplies only 784 raw pixels and start.
// DATAFLOW 0=WS, 1=OS, 2=IS. All convolutions and dense layers use the physical 5x5 grid.
module lenet_core #(
 parameter integer DATAFLOW=0,CACHE_ENABLE=0,
 parameter WEIGHT_FILE="hardware/mem/weights.hex",BIAS_FILE="hardware/mem/biases.hex",
 parameter TANH_FILE="hardware/mem/tanh.hex",EXP_FILE="hardware/mem/exp.hex")(
 input wire clk,rst,start,output wire start_ready,busy,
 input wire pixel_valid,input wire[7:0]pixel,output wire pixel_ready,
 output wire score_valid,input wire score_ready,output wire[3:0]score_index,
 output wire[15:0]probability,output wire signed[47:0]logit,
 output wire prediction_valid,input wire prediction_ready,output wire[3:0]prediction,
 output wire trace_valid,output wire[2:0]trace_layer,output wire[12:0]trace_address,
 output wire signed[15:0]trace_value,output wire trace_logit_valid,
 output reg[31:0]cycles,tile_count,output wire[31:0]weight_requests,cache_hits,l2_reads);
 localparam IDLE=0,CLEAR=1,LOAD=2,CONFIG=3,BIAS_REQ=4,BIAS_WAIT=5,SEED=6,
  A_REQ=7,A_WAIT=8,W_REQ=9,W_WAIT=10,ARRAY_START=11,ARRAY_WAIT=12,ACCUM=13,AFTER_ACC=14,
  POST_REQ=15,POST_WAIT=16,NEXT_TILE=17,LAYER_END=18,POOL_REQ=19,POOL_WAIT=20,POOL_LUT=21,POOL_WRITE=22,
  SOFT_START=23,SOFT_WAIT=24;
 reg[4:0]state;reg[2:0]layer;reg src_bank;
 reg[9:0]zero_index;reg[15:0]m_base,n_base,k_base;reg[4:0]load_index,post_index;
 reg[2:0]bias_index;reg[239:0]bias_values;reg[399:0]a_tile,b_tile;
 reg[12:0]pool_index;reg[1:0]pool_element;reg signed[15:0]pool_values[0:3];
 reg[479:0]logits;
 assign start_ready=(state==IDLE)&&!rst;assign busy=(state!=IDLE);
 wire frame_start=start&&start_ready;
 wire input_write,input_done;wire[12:0]input_address;wire signed[15:0]input_data;
 pixel_frontend u_input(clk,rst,frame_start,(state==LOAD),pixel_valid,pixel,pixel_ready,input_write,input_address,input_data,input_done);
 wire pooling;wire[15:0]positions,channels,reduction,weight_base;wire[7:0]bias_base;wire[12:0]output_words;
 layer_config u_config(layer,pooling,positions,channels,reduction,weight_base,bias_base,output_words);
 wire[15:0]a_position=m_base+load_index/5,a_k=k_base+load_index%5;
 wire a_valid=(a_position<positions)&&(a_k<reduction);
 wire[12:0]patch_read_address,pool_read_address;
 patch_address u_patch(layer,a_position,a_k,patch_read_address);
 pool_address u_pool_address(layer,pool_index,pool_element,pool_read_address);
 wire[15:0]w_channel=n_base+load_index%5,w_k=k_base+load_index/5;
 wire weight_valid=(w_channel<channels)&&(w_k<reduction);
 // Constant-coefficient address arithmetic avoids a general multiplier in address generation.
 reg[15:0]weight_address;
 always @*case(layer)
  0:weight_address=w_channel*25+w_k;
  2:weight_address=150+w_channel*150+w_k;
  4:weight_address=2550+w_channel*400+w_k;
  5:weight_address=50550+w_channel*120+w_k;
  default:weight_address=60630+w_channel*84+w_k;
 endcase
 wire w_req=(state==W_REQ)&&weight_valid;wire w_ready,w_response;wire[15:0]w_data;
 weight_memory #(.CACHE_ENABLE(CACHE_ENABLE),.INIT_FILE(WEIGHT_FILE))u_weights(
  clk,rst,w_req,w_ready,weight_address,w_response,(state==W_WAIT),w_data,weight_requests,cache_hits,l2_reads);
 wire signed[47:0]bias_data;wire bias_valid=(n_base+bias_index<channels);
 wire[7:0]bias_address=bias_base+n_base+bias_index;
 bias_rom #(.INIT_FILE(BIAS_FILE))u_bias(clk,(state==BIAS_REQ)&&bias_valid,bias_address,bias_data);
 wire array_busy,array_done;wire[1199:0]partial_tile,accumulators;
 sa_tile_engine #(.DATAFLOW(DATAFLOW))u_array(clk,rst,(state==ARRAY_START),a_tile,b_tile,array_busy,array_done,partial_tile);
 tile_accumulator u_accumulators(clk,rst,(state==SEED),(state==ACCUM),bias_values,partial_tile,accumulators);
 wire[15:0]post_position=m_base+post_index/5,post_channel=n_base+post_index%5;
 wire post_valid=(post_position<positions)&&(post_channel<channels);
 reg[12:0]post_address;
 always @*case(layer)
  0:post_address=post_channel*784+post_position;
  2:post_address=post_channel*100+post_position;
  default:post_address=post_channel;
 endcase
 wire signed[47:0]post_accumulator=$signed(accumulators[post_index*48+:48]);
 wire signed[47:0]pool_mean;
 average_pool u_pool(pool_values[0],pool_values[1],pool_values[2],pool_values[3],pool_mean);
 wire signed[15:0]activated;
 wire activation_enable=((state==POST_REQ)&&post_valid&&(layer!=6))||(state==POOL_LUT);
 tanh_lut #(.INIT_FILE(TANH_FILE))u_tanh(clk,activation_enable,(state==POOL_LUT)?pool_mean:post_accumulator,activated);
 wire read_enable=((state==A_REQ)&&a_valid)||(state==POOL_REQ);
 wire[12:0]read_address=(state==POOL_REQ)?pool_read_address:patch_read_address;
 wire signed[15:0]activation_read_data;
 wire post_write=(state==POST_WAIT)&&post_valid&&(layer!=6);
 wire pool_write=(state==POOL_WRITE);
 wire write_enable=(state==CLEAR)||input_write||post_write||pool_write;
 wire write_bank=((state==CLEAR)||input_write)?1'b0:!src_bank;
 wire[12:0]write_address=(state==CLEAR)?{3'b0,zero_index}:(input_write?input_address:(pool_write?pool_index:post_address));
 wire signed[15:0]write_data=(state==CLEAR)?16'sd0:(input_write?input_data:activated);
 activation_memory u_activations(clk,read_enable,src_bank,read_address,activation_read_data,
  write_enable,write_bank,write_address,write_data);
 assign trace_valid=post_write||pool_write;assign trace_layer=layer;assign trace_address=write_address;assign trace_value=write_data;
 assign trace_logit_valid=(state==POST_WAIT)&&post_valid&&(layer==6);
 wire soft_busy,soft_done;
 softmax10 #(.EXP_FILE(EXP_FILE))u_softmax(clk,rst,(state==SOFT_START),logits,soft_busy,soft_done,
  score_valid,score_ready,score_index,probability,logit,prediction_valid,prediction_ready,prediction);
 integer i;
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;layer<=0;src_bank<=0;zero_index<=0;m_base<=0;n_base<=0;k_base<=0;load_index<=0;post_index<=0;
   bias_index<=0;bias_values<=0;a_tile<=0;b_tile<=0;pool_index<=0;pool_element<=0;logits<=0;cycles<=0;tile_count<=0;
   for(i=0;i<4;i=i+1)pool_values[i]<=0;
  end else begin
   if(frame_start)begin cycles<=0;tile_count<=0;end else if(busy)cycles<=cycles+1'b1;
   case(state)
    IDLE:if(frame_start)begin state<=CLEAR;zero_index<=0;layer<=0;src_bank<=0;logits<=0;end
    CLEAR:if(zero_index==1023)state<=LOAD;else zero_index<=zero_index+1'b1;
    LOAD:if(input_done)state<=CONFIG;
    CONFIG:begin
     m_base<=0;n_base<=0;k_base<=0;load_index<=0;bias_index<=0;pool_index<=0;pool_element<=0;
     state<=pooling?POOL_REQ:BIAS_REQ;
    end
    BIAS_REQ:begin
     if(bias_valid)state<=BIAS_WAIT;
     else begin
      bias_values[bias_index*48+:48]<=0;
      if(bias_index==4)state<=SEED;else bias_index<=bias_index+1'b1;
     end
    end
    BIAS_WAIT:begin
     bias_values[bias_index*48+:48]<=bias_data;
     if(bias_index==4)state<=SEED;else begin bias_index<=bias_index+1'b1;state<=BIAS_REQ;end
    end
    SEED:begin k_base<=0;load_index<=0;state<=A_REQ;end
    A_REQ:begin
     if(a_valid)state<=A_WAIT;
     else begin
      a_tile[load_index*16+:16]<=0;
      if(load_index==24)begin load_index<=0;state<=W_REQ;end else load_index<=load_index+1'b1;
     end
    end
    A_WAIT:begin
     a_tile[load_index*16+:16]<=activation_read_data;
     if(load_index==24)begin load_index<=0;state<=W_REQ;end else begin load_index<=load_index+1'b1;state<=A_REQ;end
    end
    W_REQ:begin
     if(weight_valid)begin if(w_ready)state<=W_WAIT;end
     else begin
      b_tile[load_index*16+:16]<=0;
      if(load_index==24)state<=ARRAY_START;else load_index<=load_index+1'b1;
     end
    end
    W_WAIT:if(w_response)begin
     b_tile[load_index*16+:16]<=w_data;
     if(load_index==24)state<=ARRAY_START;else begin load_index<=load_index+1'b1;state<=W_REQ;end
    end
    ARRAY_START:begin tile_count<=tile_count+1'b1;state<=ARRAY_WAIT;end
    ARRAY_WAIT:if(array_done)state<=ACCUM;
    ACCUM:state<=AFTER_ACC;
    AFTER_ACC:begin
     if(k_base+5<reduction)begin k_base<=k_base+5;load_index<=0;state<=A_REQ;end
     else begin post_index<=0;state<=POST_REQ;end
    end
    POST_REQ:begin
     if(post_valid)state<=POST_WAIT;
     else if(post_index==24)state<=NEXT_TILE;else post_index<=post_index+1'b1;
    end
    POST_WAIT:begin
     if(layer==6)logits[post_channel*48+:48]<=post_accumulator;
     if(post_index==24)state<=NEXT_TILE;else begin post_index<=post_index+1'b1;state<=POST_REQ;end
    end
    NEXT_TILE:begin
     bias_index<=0;
     if(m_base+5<positions)begin m_base<=m_base+5;state<=BIAS_REQ;end
     else if(n_base+5<channels)begin n_base<=n_base+5;m_base<=0;state<=BIAS_REQ;end
     else state<=LAYER_END;
    end
    LAYER_END:begin
     if(layer==6)state<=SOFT_START;
     else begin src_bank<=!src_bank;layer<=layer+1'b1;state<=CONFIG;end
    end
    POOL_REQ:state<=POOL_WAIT;
    POOL_WAIT:begin
     pool_values[pool_element]<=activation_read_data;
     if(pool_element==3)state<=POOL_LUT;else begin pool_element<=pool_element+1'b1;state<=POOL_REQ;end
    end
    POOL_LUT:state<=POOL_WRITE;
    POOL_WRITE:begin
     if(pool_index+1<output_words)begin pool_index<=pool_index+1'b1;pool_element<=0;state<=POOL_REQ;end
     else state<=LAYER_END;
    end
    SOFT_START:state<=SOFT_WAIT;
    SOFT_WAIT:if(soft_done)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
