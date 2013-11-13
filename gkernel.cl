/*
--test commit

gkernel v0.01 

pyopencl genetic fitness kernel

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
*/

#define MAX_WORKGROUP_SIZE 32
#define MAX_OPEN_ORDERS 256
#define COMMISION 0.012
#define STBF 1.08
#define NLSF 3.0
#define KILL_SCORE -10001
#define ORDER_RECORD_LENGTH 16

__kernel void fitness(__global float* shares,__global uint* wll,__global uint* wls,__global uint* buy_wait,__global float* markup,
			__global float* stop_loss,__global float* stop_age,__global float* macd_buy_trip,
			__global uint* buy_wait_after_stop_loss,__global uint* quartile,
			__global uint* market_classification,__global float* input,
			__global float* score,__global float* orders,const uint input_len)
{
	__private int gid = get_global_id(0);

	/*calculate the ema weighting multipliers*/
	__private float ema_short_mult = (2.0 / (wls[gid] + 1) );
	__private float ema_long_mult = (2.0 / (wll[gid] + 1) );
	__private float ema_short = 0;
	__private float ema_long = 0;
	__private float macd_pct = 0.0;
	__private float balance = 10000.00;
	__private float wins = 0.0;
	__private float loss = 0.0;
	__private uint buy_delay = 1000;
	__private float t = 0.0; /*time period*/
	__private uint orders_index = 0;
	__private uint last_orders_index = 0;
	__private bool sell = false;
	__private bool proceed_with_order = false;
	__private uint k = 0;
	__private ulong j = 0;

	/*zero the orders array*/
	for (k=0; k < MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH; k++){orders[k + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = -1.0 * (float)gid;}

	score[gid] = 0.0;

	for (j=0; j < input_len; j++)
	{
		t += 1.0;
		ema_long = (input[j] - ema_long) * ema_long_mult + ema_long;
		ema_short = (input[j] - ema_short) * ema_short_mult + ema_short;
		//macd_abs = ema_short - ema_long;
		macd_pct = ((ema_short - ema_long) / (ema_short + 0.00001));

		if (buy_delay > 0){ buy_delay -= 1; }

		score[gid] *= 0.99999; /* older orders get penalized */

		/*only look for buy orders within the directed quartile and only if the balance can support a buy order and the macd buy trigger tripped*/
		if ((market_classification[j] == quartile[gid]) & (balance > (input[j] * shares[gid])) & (buy_delay == 0) & (macd_pct < macd_buy_trip[gid]))
		{
			proceed_with_order = true;

			/*find an empty order slot in the array*/
			last_orders_index = orders_index;
			while (orders[orders_index + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] > 0.5 & proceed_with_order == true)
			{				
				orders_index += ORDER_RECORD_LENGTH;
				if (orders_index >= MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH) {orders_index = 0;}
				if (last_orders_index == orders_index){proceed_with_order = false;}
			}
			
			if (proceed_with_order == true)
			{
				buy_delay += buy_wait[gid];
				balance -= input[j] * shares[gid];
				orders[orders_index + 0 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = t;
				orders[orders_index + 1 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = input[j];
				orders[orders_index + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = input[j] * (1.0 + markup[gid] + COMMISION);
				orders[orders_index + 3 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = input[j] * (1.0 - stop_loss[gid]);
				orders[orders_index + 4 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = t + stop_age[gid];
				orders[orders_index + 5 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = -1234.0;//this is where the score goes
				/* used for debug:				
				orders[orders_index + 6 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = ema_short; //the rest is for debug
				orders[orders_index + 7 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = ema_long;
				orders[orders_index + 8 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = macd_pct;
				orders[orders_index + 9 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = macd_buy_trip[gid];
				orders[orders_index + 10+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = balance;
				orders[orders_index + 11+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = (wins-loss);
				orders[orders_index + 12+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = (float) market_classification[j];
				orders[orders_index + 13+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = (float) quartile[j];
				orders[orders_index + 14+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = shares[gid];
				orders[orders_index + 15+ (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = (float) orders_index;
				*/
				orders_index += ORDER_RECORD_LENGTH;
				if (orders_index >= MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH) {orders_index = 0;}
			}
		}

		/*check open orders to see if it't time to sell*/
		for (k=0; k < MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH; k+=ORDER_RECORD_LENGTH)
		{
			if (orders[k + 0 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] > 0.5)
			{
				sell = false;
				/*check for stop age*/
				if (orders[k + 4 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] <= t)
				{
					loss += 1.0;
					sell = true;
					buy_delay += buy_wait_after_stop_loss[gid];
					score[gid] += -2.0 + ( input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]);
					orders[k + 5 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = -2.0 + ( input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]);
				}
				/*check for stop loss*/
				else if (orders[k + 3 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] >= input[j])
				{
					loss += 0.9;
					sell = true;
					buy_delay += buy_wait_after_stop_loss[gid];
					score[gid] += -2.0 + ( input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]); // -1 * (1 - price/target)
					orders[k + 5 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = -2.0 + ( input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]);
				}

				/*check target price*/
				else if (orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] <= input[j])
				{
					wins += 1.0;
					sell = true;					
					//score[gid] +=  markup[gid] * 100.0 * (1.0 / pow(1.0 + t - orders[k + 0 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)],STBF)) * (exp((NLSF/1000000.0) * orders[k + 0 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]));// * shares[gid];
					score[gid] += input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)];
					orders[k + 5 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = input[j] / orders[k + 2 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)]; 
				}

				if (sell == true)
				{
					orders[k + 0 + (gid * MAX_OPEN_ORDERS * ORDER_RECORD_LENGTH)] = 0.1;
					balance += input[j] * shares[gid] * (1.0 - COMMISION);
					sell = false;
				}
			}
		}

		/* at the end of the dataset */
		if (j == (input_len - 1))
		{
			if (score[gid] == 0.0){
				score[gid] = KILL_SCORE;
			}
			else 
			{

				/* because stop loss will generaly be higher that the target (markup) percentage */
				/* the loss count needs to be weighted by the pct difference */
				//loss_weighting_factor = 1.0 + (stop_loss[gid] / (markup[gid] + 0.0001));
			
				
				/* fine tune the score */
				score[gid] += (float)buy_wait[gid] / 1000.0;
				score[gid] += (float)buy_wait_after_stop_loss[gid] / 1000.0;
				score[gid] -= (stop_loss[gid] * 1000.0);
				//final_score_balance += ((float)wls[gid] / 10000.0);
				score[gid] -= (stop_age[gid] / 1000.0);
				score[gid] += shares[gid];

				score[gid] *= wins / (0.00001 + wins + (loss * (1.0 + (stop_loss[gid] / (markup[gid] + 0.0001)))));//wins / (0.00001 + wins + (loss * loss_weighting_factor));
				score[gid] *= 1.0 + markup[gid];

				/* severly penalize the score if the win/ratio is less than 85% % */
				if (wins / (wins + loss) < 0.85)
				{
					score[gid] /= 100000.0;
				}

				return;

			}
		}		
	}
}

