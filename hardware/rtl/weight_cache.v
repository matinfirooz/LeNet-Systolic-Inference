`timescale 1ns/1ps
// Exactly 512 x 16 data bits = 1 KiB. 64 direct-mapped lines, eight words/line.
// A hit retires one clock after acceptance. Misses refill from the four-cycle L2.
module weight_cache #(parameter integer DEPTH=61470)(
 input wire clk,rst,req_valid,output wire req_ready,input wire[15:0]req_address,
 output wire resp_valid,input wire resp_ready,output reg[15:0]resp_data,
 output wire l2_req_valid,input wire l2_req_ready,output wire[15:0]l2_req_address,
 input wire l2_resp_valid,output wire l2_resp_ready,input wire[15:0]l2_resp_data,
 output reg[31:0]request_count,hit_count);
 localparam IDLE=0,MISS_REQ=1,MISS_WAIT=2,RESP=3;
 reg[1:0]state;reg[15:0]saved;reg[2:0]offset;reg[15:0]selected;
 (* ram_style="block" *) reg[15:0]data[0:511];
 reg[6:0]tags[0:63];reg[63:0]valid;
 wire[16:0]fill_address={1'b0,saved[15:3],3'b000}+offset;
 wire[16:0]next_fill_address=fill_address+17'd1;
 wire chain_read=(state==MISS_WAIT)&&l2_resp_valid&&(offset<7)&&(next_fill_address<DEPTH);
 assign req_ready=(state==IDLE);assign resp_valid=(state==RESP);
 // Retire one L2 word and launch the next on the same edge: four-clock refill II.
 assign l2_req_valid=((state==MISS_REQ)&&(fill_address<DEPTH))||chain_read;
 assign l2_req_address=chain_read?next_fill_address[15:0]:fill_address[15:0];
 assign l2_resp_ready=(state==MISS_WAIT);
 integer i;
 always @(posedge clk)begin
  if(rst)begin state<=IDLE;saved<=0;offset<=0;selected<=0;valid<=0;resp_data<=0;request_count<=0;hit_count<=0;for(i=0;i<64;i=i+1)tags[i]<=0;end
  else case(state)
   IDLE:if(req_valid)begin
    saved<=req_address;request_count<=request_count+1'b1;
    if(valid[req_address[8:3]]&&tags[req_address[8:3]]==req_address[15:9])begin
     resp_data<=data[req_address[8:0]];hit_count<=hit_count+1'b1;state<=RESP;
    end else begin offset<=0;selected<=0;state<=MISS_REQ;end
   end
   MISS_REQ:begin
    if(fill_address>=DEPTH)begin
     data[{saved[8:3],offset}]<=0;
     if(offset==7)begin valid[saved[8:3]]<=1;tags[saved[8:3]]<=saved[15:9];resp_data<=selected;state<=RESP;end
     else offset<=offset+1'b1;
    end else if(l2_req_ready)state<=MISS_WAIT;
   end
   MISS_WAIT:if(l2_resp_valid)begin
    data[{saved[8:3],offset}]<=l2_resp_data;
    if(offset==saved[2:0])selected<=l2_resp_data;
    if(offset==7)begin
     valid[saved[8:3]]<=1;tags[saved[8:3]]<=saved[15:9];resp_data<=(saved[2:0]==7)?l2_resp_data:selected;state<=RESP;
    end else begin offset<=offset+1'b1;state<=(chain_read&&l2_req_ready)?MISS_WAIT:MISS_REQ;end
   end
   RESP:if(resp_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
