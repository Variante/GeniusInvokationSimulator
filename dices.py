from utils import *

class Dices:
    def __init__(self):
        self.options = load_js('Dices')
        self.l = len(self.options)

    def _count_to_dict(self, count):
        return {t: c for t, c in zip(self.options, count)}
        
    def _dict_to_count(self, d):
        return np.array([d.get(i, 0) for i in self.options], dtype=np.uint8)
        
    def random_type(self):
        # don't roll Omni
        return np.random.randint(0, self.l - 1)
        
    def roll(self, total_num=8, keep=None):
        if keep is None:
            keep = np.zeros(self.l, dtype=np.uint8)
        else:
            if isinstance(keep, list):
                keep = np.array(keep)
            if isinstance(keep, dict):
                keep = self._dict_to_count(keep)
            assert np.sum(keep) <= total_num
            assert keep.shape[0] == self.l
            
        results = np.random.randint(0, self.l, total_num - np.sum(keep))
        count = np.bincount(results, minlength=self.l)
        count += keep
        return self._count_to_dict(count)


if __name__ == '__main__':
    d = Dices()
    for i in range(10):
        keep = np.array([0] * 8)
        keep[i % 8] += i % 8
        r, c = d.roll(keep=keep)
        print(r, c)
        