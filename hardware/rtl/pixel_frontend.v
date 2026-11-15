`timescale 1ns/1ps
module pixel_frontend(input wire clk,rst,frame_start,enable,input wire pixel_valid,
 input wire[7:0]pixel,output wire pixel_ready,write_valid,output wire[12:0]write_address,
 output wire signed[15:0]write_data,output wire frame_done);
 reg[9:0]index;
 assign pixel_ready=enable&&!rst&&(index<784);assign write_valid=pixel_valid&&pixel_ready;
 assign write_address=(index/28+2)*32+index%28+2;
 assign write_data=({pixel,12'b0}+20'd127)/20'd255;
 assign frame_done=write_valid&&(index==783);
 always @(posedge clk)if(rst||frame_start)index<=0;else if(write_valid)index<=index+1'b1;
endmodule
