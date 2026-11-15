import gzip,hashlib,math,unittest
from pathlib import Path
import numpy as np
from software.data import FILES,load_idx,split_indices
from software.fixed_point import conv_integer,pool_integer,tanh_acc,quantize,infer_integer
ROOT=Path(__file__).resolve().parents[1]

class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.weights=dict(np.load(ROOT/'software/trained_weights.npz'));cls.q,_=quantize(cls.weights)
    def test_parameter_layout(self):
        self.assertEqual(sum(v.size for v in self.weights.values()),61706)
        self.assertEqual(self.weights['conv3.weight'].shape,(16,6,5,5))
        self.assertEqual(self.weights['conv5.weight'].shape,(120,16,5,5))
    def test_dataset_checksums_and_split(self):
        for name,expected in FILES.items():self.assertEqual(hashlib.md5((ROOT/'data/fashion'/name).read_bytes()).hexdigest(),expected)
        raw,y=load_idx(ROOT/'data/fashion');a,b=split_indices(y)
        self.assertEqual((len(a),len(b)),(54000,6000));self.assertFalse(set(a)&set(b));self.assertEqual(len(set(a)|set(b)),60000)
        self.assertTrue(np.all(np.bincount(y[b])==600))
    def test_normalization_and_border(self):
        x=np.arange(256,dtype=np.int64);v=(x*4096+127)//255
        self.assertEqual((v[0],v[-1]),(0,4096));self.assertTrue(np.all(np.diff(v)>0))
        padded=np.pad(np.full((28,28),4096),2)
        self.assertEqual(padded.shape,(32,32));self.assertEqual(np.count_nonzero(padded),784)
    def test_integer_convolution_independent_scalar(self):
        x=(np.arange(72).reshape(1,2,6,6)-36).astype(np.int64)*64
        w=(np.arange(100).reshape(2,2,5,5)%7-3).astype(np.int64)*128;b=np.array([17000,-33000])
        actual=conv_integer(x,w,b,self.q['tanh_lut']);expected=np.zeros_like(actual)
        for n in range(2):
            for y in range(2):
                for z in range(2):
                    acc=int(b[n])
                    for ch in range(2):
                        for ky in range(5):
                            for kx in range(5):acc+=int(x[0,ch,y+ky,z+kx])*int(w[n,ch,ky,kx])
                    coordinate=max(-2048,min(2048,math.floor(acc/65536+.5)))
                    expected[0,n,y,z]=math.floor(math.tanh(coordinate/256)*4096+.5)
        np.testing.assert_array_equal(actual,expected)
    def test_pool_exact_mean_before_lookup(self):
        x=np.array([[[[32,0,-32,0],[0,0,0,0],[4096,4096,-4096,-4096],[4096,4096,-4096,-4096]]]],dtype=np.int64)
        actual=pool_integer(x,self.q['tanh_lut']);expected=np.zeros_like(actual)
        for y in range(2):
            for z in range(2):
                total=sum(int(x[0,0,y*2+dy,z*2+dx]) for dy in range(2) for dx in range(2))
                coord=max(-2048,min(2048,math.floor(total/64+.5)))
                expected[0,0,y,z]=math.floor(math.tanh(coord/256)*4096+.5)
        np.testing.assert_array_equal(actual,expected)
    def test_lut_full_domain_and_signed_extremes(self):
        values=self.q['tanh_lut'];self.assertTrue(np.all(np.diff(values)>=0));self.assertEqual(values[2048],0)
        x=np.array([-(1<<47),(1<<47)-1,0],dtype=np.int64)
        np.testing.assert_array_equal(tanh_acc(x,values),[-4096,4096,0])
    def test_accumulator_domain_bounds(self):
        for name in ['conv1','conv3','conv5','fc6','fc7']:
            bound=np.abs(self.q[name+'.weight']).reshape(self.q[name+'.weight'].shape[0],-1).sum(1)*4096+np.abs(self.q[name+'.bias'])
            self.assertTrue(np.all(bound<(1<<47)))
    def test_exported_image_and_probability_mass(self):
        raw,labels=load_idx(ROOT/'data/fashion','t10k');result=infer_integer(raw[:4],self.q,True)
        saved=np.load(ROOT/'results/software/integer_test_outputs.npz')
        np.testing.assert_array_equal(result['logits'],saved['logits'][:4]);self.assertEqual(result['trace'].shape,(4,8084))
        total=result['probabilities'].sum(1);self.assertTrue(np.all((total>=65526)&(total<=65536)))
        self.assertTrue(np.all(result['probabilities']>=0));np.testing.assert_array_equal(result['predictions'],saved['predictions'][:4])

if __name__=='__main__':unittest.main()
