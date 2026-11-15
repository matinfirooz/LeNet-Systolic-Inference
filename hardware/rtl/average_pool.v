`timescale 1ns/1ps
module average_pool(input wire signed[15:0]a,b,c,d,output wire signed[47:0]mean_q24);
 wire signed[17:0]sum=$signed({{2{a[15]}},a})+$signed({{2{b[15]}},b})+$signed({{2{c[15]}},c})+$signed({{2{d[15]}},d});
 assign mean_q24=$signed({{30{sum[17]}},sum})<<<10;
endmodule
