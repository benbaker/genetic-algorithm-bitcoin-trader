# get yahoo stock data
# - downloads
# - converts
# - stores
import urllib
import time
import datetime

def convert_date_format(date):
    return time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())


goog_base_url = "http://www.google.com/finance/getprices?q={Code}&x={Exchange}&i={Interval}&p={Period}&f=d,c,h,l,o,v"
#http://www.google.com/finance/getprices?q=DPS&x=NYSE&i=60&p=1d&f=d,c,h,l,o,v

base_url = "http://ichart.finance.yahoo.com/table.csv?s=%s&a=08&b=7&c=2008&d=11&e=22&f=2012&g=d&ignore=.csv"
#"http://ichart.finance.yahoo.com/table.csv?s="

def make_url(ticker_symbol):
    return base_url%ticker_symbol

def make_google_url(ticker_symbol,exchange):
    ret = goog_base_url.replace('{Code}',ticker_symbol).replace('{Exchange}',exchange).replace('{Interval}','60').replace('{Period}','1w')
    print ret
    return ret


output_path = "../datafeed/"

def pull_historical_data(ticker_symbol):
    filename = output_path + "yahoo_"+ticker_symbol + ".csv"
    try:
        urllib.urlretrieve(make_url(ticker_symbol), filename)
    except urllib.ContentTooShortError as e:
        outfile = open(filename, "w")
        outfile.write(e.content)
        outfile.close()

    return  filename

def pull_google_historical_data(ticker_symbol,exchange):
    filename = output_path + "google_"+ticker_symbol + ".csv"
    try:
        urllib.urlretrieve(make_google_url(ticker_symbol,exchange), filename)
    except urllib.ContentTooShortError as e:
        outfile = open(filename, "w")
        outfile.write(e.content)
        outfile.close()

    return  filename




if __name__ == "__main__":
    print "Enter stock symbol to retreive:"
    sym = raw_input()
    fn = pull_historical_data(sym)
    print "Downloaded:",fn
    #convert the format
    f = open(fn,'r')
    data = f.readlines()
    data = data[1:]
    data.reverse()
    f.close()
    f = open(fn,'w')
    for row in data:    #skip the header row
        sr = row.replace('\n','').split(',')
        ts = str(convert_date_format(sr[0]))
        f.write(",".join((ts,sr[4],sr[5]))+'\n')
    f.close()
    print "Converted:",fn
    print "Data is ready to use."

    #pull_google_historical_data(ticker_symbol,exchange)
    #fn = pull_google_historical_data('DPS','NYSE')






