/*
gkernel v0.01 

pyopencl macd kernel

Copyright 2011 Brian Monkaba

This file is part of ga-bitbot.

    ga-bitbot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ga-bitbot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ga-bitbot.  If not, see <http://www.gnu.org/licenses/>.


Development device parameters:
	Max compute units:                             14
	Max work items dimensions:                     3
	Max work items[0]:                           256
	Max work items[1]:                           256
	Max work items[2]:                           256
	Max work group size:                           256
	Max memory allocation:                         536870912
	Max size of kernel argument:                   1024
	Global memory size:                            1073741824
	Constant buffer size:                          65536
	Max number of constant args:                   8
	Local memory type:                             Scratchpad
	Local memory size:                             32768
	Kernel Preferred work group size multiple:     64

Work Plan:
1073741824 (bytes) = 268435456 floats (32 bit)
- 1M float inputs = 267435456
/ 14 compute units = 19102532 per compute unit

/ 1M input = 19 work items
or
64 work items @ 298K inputs

64 * 24 = 1536 bytes of private memory per compute unit

check:
64*14*275k * 4 bytes (32bit floats) = 985,600,000 bytes = 88,141,824 bytes left over

*/
#pragma OPENCL EXTENSION cl_amd_printf : enable

#define WORK_GROUP_SIZE 6
#define WORK_ITEM_SIZE 128


__kernel void macd(__global float* macd_pct,__global uint* wll,__global uint* wls,__global float* input,const uint input_len)
{

	/* private vars (24 bytes)*/
	__private int global_id = get_global_id(0);
	__private int group_id = get_group_id(0);
	__private int local_id = get_local_id(0);

	__private float ema_short_mult = (2.0 / (wls[global_id] + 1) );
	__private float ema_long_mult = (2.0 / (wll[global_id] + 1) );
	__private float ema_short = 0;
	__private float ema_long = 0;

	//printf("[%d,%d,%d]",group_id,local_id,global_id);

	for (uint j=0; j < input_len; j++)
	{
		ema_long = (input[j] - ema_long) * ema_long_mult + ema_long;
		ema_short = (input[j] - ema_short) * ema_short_mult + ema_short;


		macd_pct[(global_id * input_len) + j] = (float)global_id;//((ema_short - ema_long) / (ema_short + 0.00001));
		mem_fence(CLK_LOCAL_MEM_FENCE | CLK_GLOBAL_MEM_FENCE);
	}
}


// optimized parrallel storage array indexing: (group_id * input_len * WORK_ITEM_SIZE) + (input_len * j) + local_id
//simple indexing: (global_id * input_len) + j

