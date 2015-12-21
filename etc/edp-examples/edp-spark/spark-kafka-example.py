# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import sys

from pyspark import SparkContext
from pyspark.streaming.kafka import KafkaUtils
from pyspark.streaming import StreamingContext


def main():
    if len(sys.argv) != 4:
        print("Usage: kafka_wordcount.py <zk> <topic> <timeout>",
              file=sys.stderr)
        exit(-1)

    sc = SparkContext(appName="PythonStreamingKafkaWordCount")
    ssc = StreamingContext(sc, 1)
    timeout = None
    if len(sys.argv) == 4:
        zk, topic, timeout = sys.argv[1:]
        timeout = int(timeout)
    else:
        zk, topic = sys.argv[1:]
    kvs = KafkaUtils.createStream(
        ssc, zk, "spark-streaming-consumer", {topic: 1})
    lines = kvs.map(lambda x: x[1])
    counts = lines.flatMap(lambda line: (line.split(" "))
                           .map(lambda word: (word, 1))
                           .reduceByKey(lambda a, b: a+b))
    counts.pprint()
    kwargs = {}
    if timeout:
        kwargs['timeout'] = timeout
    ssc.start()
    ssc.awaitTermination(**kwargs)
