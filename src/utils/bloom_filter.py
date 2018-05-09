from array import array
from hashlib import md5

from redis import Redis


class SimpleHash:
    def __init__(self, cap, seed):
        self.cap = cap
        self.seed = seed

    def hash(self, value):
        ret = 0
        for i in range(len(value)):
            ret += self.seed * ret + ord(value[i])
        return (self.cap - 1) & ret


class BloomFilter:
    """
    布隆过滤器
    原理为：先生成一个长度为固定，且全为0的集合，然后开始逐一对要比较的元素进行多次哈希，然后在集合中将多次结果
    的值对应的位置为1，如此类推，若发现某一元素所有要插入的位置都已经为1了，则说明这个元素重复了。
    关键参数：n个元素，集合大小为m，k次哈希
    具体误判率可以查表：http://pages.cs.wisc.edu/~cao/papers/summary-cache/node8.html
    """

    def __init__(self, bit_size=1 << 23, seeds=None, mapper=None):
        """
        默认参数下，误判率为8.56e-05
        :param bit_size: m值
        :param seeds: k值
        """
        self._bit_size = bit_size
        if seeds is None:
            seeds = [3, 5, 7, 11, 13, 31, 67]
        self._seeds = seeds
        if mapper is None:  # 初始化
            mapper = array('b', [0 for _ in range(self._bit_size)])  # 选择了用数组来存放记录，可以改用其他的结构，例如redis的bitmap
        self._map = mapper
        self._hash_functions = []
        for seed in self._seeds:
            self._hash_functions.append(SimpleHash(self._bit_size, seed))

    def is_contain(self, ele):  # 判断是否存在
        m5 = md5()
        m5.update(bytes(ele, encoding='utf-8'))
        _ele = m5.hexdigest()
        return all(self._map[f.hash(_ele)] for f in self._hash_functions)

    def insert(self, ele):  # 参入新值
        m5 = md5()
        m5.update(bytes(ele, encoding='utf-8'))
        _ele = m5.hexdigest()
        for f in self._hash_functions:
            index = f.hash(_ele)
            self._map[index] = 1


class RedisAdapter:
    def __init__(self, redis, key_name):
        if redis is None:
            redis = Redis(db=2)
        self.redis = redis
        self.key_name = key_name

    def __getitem__(self, item):
        return self.redis.getbit(self.key_name, item)

    def __setitem__(self, key, value):
        return self.redis.setbit(self.key_name, key, value)


class MyBloomFilter(BloomFilter):
    def __init__(self, redis=None, key_name='shuiwujia:bf', **kwargs):
        super().__init__(**kwargs)
        self._map = RedisAdapter(redis, key_name)


if __name__ == '__main__':
    # bf = BloomFilter()
    bf = MyBloomFilter()
    bb = ' http://www.bdc.cn/biz200/mh204XwdtAction!getNewsContent.act?viewObj.newsId=8a82804d6187a83f01618e7cbae426c9'
    print(bf.is_contain(bb))
    # bf.insert(bb)
    # print(bf.is_contain(bb))
    # s1 = 'https://bing.com'
    # s2 = 'https://google.com'
    # s3 = 'http://google.com'
    # for s in [s1, s2]:
    #     bf.insert(s)
    # for s in [s1, s2, s3]:
    #     print(bf.is_contain(s))
