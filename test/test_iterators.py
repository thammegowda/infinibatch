import copy
import itertools
from random import Random
import unittest

from infinibatch.iterators import *

if __name__ == "__main__":
    unittest.main()


class TestBase(unittest.TestCase):
    def setUp(self):
        self.lengths = [1, 2, 3, 4, 5, 42, 157, 256, 997]
        self.world_sizes = [1, 2, 3, 4, 5, 11, 16, 128, 255, 774]
        self.seed = 42

    def assertMultisetEqual(self, a, b):
        def list_to_dict(l):
            d = {}
            for item in l:
                d[item] = d.get(item, 0) + 1
            return d

        self.assertEqual(list_to_dict(a), list_to_dict(b))


class TestFiniteIteratorMixin:
    """
    Mixin to be used in combination with TestBase
    to test basic function of finite CheckpointableIterators
    """

    def test_basic(self):
        for case_name, expected_result, it in self.test_cases:
            with self.subTest(case_name):
                result = list(it)
                self.assertEqual(result, expected_result)


class TestFiniteIteratorCheckpointingMixin:
    """
    Mixin to be used in combination with TestBase
    to test checkpointing functionality of finite CheckpointableIterators
    """

    def test_checkpointing_reset(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)  # extract data
                it.setstate(None)  # reset to start
                result = list(it)
                self.assertEqual(result, expected_result)

    def test_checkpointing_from_start(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                checkpoint = it.getstate()
                expected_result = list(it)  # extract data
                it.setstate(checkpoint)  # reset to start
                result = list(it)
                self.assertEqual(result, expected_result)

    def _test_checkpointing_from_pos(self, it, pos):
        for _ in range(pos):  # go to pos
            next(it)
        checkpoint = it.getstate()  # take checkpoint
        expected_result = list(it)  # extract data
        it.setstate(checkpoint)  # reset to checkpoint
        result = list(it)
        self.assertEqual(result, expected_result)

    def test_checkpointing_from_one(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                pos = 1
                self._test_checkpointing_from_pos(it, pos)

    def test_checkpointing_from_quarter(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)
                it.setstate(None)
                pos = len(expected_result) // 4
                self._test_checkpointing_from_pos(it, pos)

    def test_checkpointing_from_third(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)
                it.setstate(None)
                pos = len(expected_result) // 3
                self._test_checkpointing_from_pos(it, pos)

    def test_checkpointing_from_half(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)
                it.setstate(None)
                pos = len(expected_result) // 2
                self._test_checkpointing_from_pos(it, pos)

    def test_checkpointing_before_end(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)
                it.setstate(None)
                pos = len(expected_result) - 1
                self._test_checkpointing_from_pos(it, pos)

    def test_checkpointing_at_end(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                list(it)  # exhaust iterator
                checkpoint = it.getstate()  # take checkpoint
                it.setstate(None)  # reset to beginning
                it.setstate(checkpoint)  # reset to checkpoint
                self.assertRaises(StopIteration, it.__next__)

    def test_checkpointing_complex(self):
        for case_name, _, it in self.test_cases:
            with self.subTest(case_name):
                expected_result = list(it)

                # get a bunch of checkpoints at different positions
                it.setstate(None)
                positions = [
                    0,
                    len(expected_result) // 7,
                    len(expected_result) // 6,
                    len(expected_result) // 5,
                    len(expected_result) // 4,
                    len(expected_result) // 3,
                    len(expected_result) // 2,
                ]
                checkpoints = []
                for i in range(len(positions)):
                    offset = positions[i] - positions[i - 1] if i > 0 else positions[0]
                    for _ in range(offset):
                        next(it)
                    checkpoints.append(it.getstate())

                # check that iterator returns correct result at all checkpoints
                for pos, checkpoint in zip(positions, checkpoints):
                    it.setstate(checkpoint)
                    self.assertEqual(list(it), expected_result[pos:])

                # check that iterator returns correct result at all checkpoints in reverse order
                tuples = list(zip(positions, checkpoints))
                tuples.reverse()
                for pos, checkpoint in tuples:
                    it.setstate(checkpoint)
                    self.assertEqual(list(it), expected_result[pos:])

                # check that iterator returns correct result at all checkpoints
                # while resetting between any two checkpoints
                for pos, checkpoint in zip(positions, checkpoints):
                    it.setstate(None)
                    it.setstate(checkpoint)
                    self.assertEqual(list(it), expected_result[pos:])

                # and as the grand finale: reset and check again
                it.setstate(None)
                result = list(it)
                self.assertEqual(result, expected_result)


class TestInfinitePermutationSourceIterator(TestBase):
    def setUp(self):
        super().setUp()
        self.repeats = [1, 2, 3, 4, 5]

    def test_no_shuffle(self):
        for n, k in itertools.product(self.lengths, self.repeats):
            with self.subTest(f"n={n}, k={k}"):
                data = list(range(n))
                it = InfinitePermutationSourceIterator(copy.deepcopy(data), shuffle=False)
                result = [next(it) for _ in range(k * n)]
                self.assertEqual(data * k, result)

    def test_shuffle(self):
        for n, k in itertools.product(self.lengths, self.repeats):
            with self.subTest(f"n={n}, k={k}"):
                data = list(range(n))
                it = InfinitePermutationSourceIterator(copy.deepcopy(data))
                result = [next(it) for _ in range(k * n)]
                self.assertMultisetEqual(data * k, result)

    def test_checkpointing_from_start(self):
        for n, k in itertools.product(self.lengths, self.repeats):
            with self.subTest(f"n={n}, k={k}"):
                data = list(range(n))
                it = InfinitePermutationSourceIterator(copy.deepcopy(data))
                expected_result = [next(it) for _ in range(k * n)]  # extract data
                it.setstate(None)  # reset to start
                result = [next(it) for _ in range(k * n)]
                self.assertEqual(result, expected_result)

    def test_checkpointing_from_middle(self):
        for n, k in itertools.product(self.lengths, self.repeats):
            with self.subTest(f"n={n}, k={k}"):
                data = list(range(n))
                it = InfinitePermutationSourceIterator(copy.deepcopy(data))
                checkpoint_pos = k * n // 3
                for _ in range(checkpoint_pos):  # go to checkpoint_pos
                    next(it)
                checkpoint = it.getstate()  # take checkpoint
                expected_result = [next(it) for _ in range(k * n)]  # extract data
                for _ in range(checkpoint_pos):  # move forward some more
                    next(it)
                it.setstate(checkpoint)  # reset to checkpoint
                result = [next(it) for _ in range(k * n)]  # get data again
                self.assertEqual(result, expected_result)

    def test_checkpointing_at_boundary(self):
        for n, k in itertools.product(self.lengths, self.repeats):
            with self.subTest(f"n={n}, k={k}"):
                data = list(range(n))
                it = InfinitePermutationSourceIterator(copy.deepcopy(data))
                checkpoint_pos = k * n
                for _ in range(checkpoint_pos):  # go to checkpoint_pos
                    next(it)
                checkpoint = it.getstate()  # take checkpoint
                expected_result = [next(it) for _ in range(k * n)]  # extract data
                for _ in range(checkpoint_pos):  # move forward some more
                    next(it)
                it.setstate(checkpoint)  # reset to checkpoint
                result = [next(it) for _ in range(k * n)]  # get data again
                self.assertEqual(result, expected_result)

    # this test currently hangs / fails because of a bug
    # def test_multiple_instances(self):
    #     world_sizes = [1, 2, 3, 4, 5, 11, 16, 128, 255, 774]
    #     for n, k, num_instances in itertools.product(self.lengths, self.repeats, world_sizes):
    #         data = list(range(n))
    #         it = InfinitePermutationSourceIterator(copy.deepcopy(data))
    #         single_instance_data = [next(it) for _ in range(k * n * num_instances)]
    #         for instance_rank in range(num_instances):
    #             with self.subTest(f"n={n}, k={k}, num_instances={num_instances}, instance_rank={instance_rank}"):
    #                 it = InfinitePermutationSourceIterator(
    #                     copy.deepcopy(data), num_instances=num_instances, instance_rank=instance_rank
    #                 )
    #                 expected_data = []
    #                 pos = instance_rank
    #                 while len(expected_data) < k * n:
    #                     expected_data.append(data[pos])
    #                     pos += instance_rank
    #                 result = [next(it) for _ in range(k * n)]
    #                 self.assertEqual(expected_data, result)

    def test_empty_source(self):
        def create_iterator():
            it = InfinitePermutationSourceIterator([])

        self.assertRaises(ValueError, create_iterator)

    def test_rank_too_large(self):
        def create_iterator():
            it = InfinitePermutationSourceIterator([1], num_instances=2, instance_rank=2)

        self.assertRaises(ValueError, create_iterator)


class TestChunkedSourceIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            data = list(range(n))
            it = ChunkedSourceIterator(copy.deepcopy(data))
            self.test_cases.append((f"n={n}", data, it))

    def test_multiple_instances(self):
        for n, num_instances in itertools.product(self.lengths, self.world_sizes):
            with self.subTest(f"n={n}, num_instances={num_instances}"):
                data = list(range(n))
                result = []
                sizes = []
                for instance_rank in range(num_instances):
                    it = ChunkedSourceIterator(
                        copy.deepcopy(data), num_instances=num_instances, instance_rank=instance_rank
                    )
                    output = list(it)
                    result.extend(output)
                    sizes.append(len(output))
                self.assertEqual(data, result)
                self.assertTrue(max(sizes) - min(sizes) <= 1)  # make sure data is split as evenly as possible

    def test_rank_too_large(self):
        def create_iterator():
            it = ChunkedSourceIterator([1], num_instances=2, instance_rank=2)

        self.assertRaises(ValueError, create_iterator)


class TestSamplingRandomMapIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    @staticmethod
    def transform(random, item):
        return item + random.random()

    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            data = list(range(n))
            random = Random()
            random.seed(self.seed)
            expected_result = [n + random.random() for n in data]
            it = SamplingRandomMapIterator(NativeCheckpointableIterator(data), transform=self.transform, seed=self.seed)
            self.test_cases.append((f"n={n}", expected_result, it))


class TestMapIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    @staticmethod
    def transform(item):
        return 2 * item

    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            data = list(range(n))
            expected_result = [self.transform(item) for item in data]
            it = MapIterator(NativeCheckpointableIterator(data), self.transform)
            self.test_cases.append((f"n={n}", expected_result, it))


class TestZipIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []

        # pairs
        for n in self.lengths:
            data1 = list(range(n))
            data2 = [item * item for item in data1]
            expected_result = list(zip(data1, data2))
            it = ZipIterator(NativeCheckpointableIterator(data1), NativeCheckpointableIterator(data2))
            self.test_cases.append((f"n={n}, pairs", expected_result, it))

        # triples
        for n in self.lengths:
            data1 = list(range(n))
            data2 = [item * item for item in data1]
            data3 = [item * item for item in data2]
            expected_result = list(zip(data1, data2, data3))
            it = ZipIterator(
                NativeCheckpointableIterator(data1),
                NativeCheckpointableIterator(data2),
                NativeCheckpointableIterator(data3),
            )
            self.test_cases.append((f"n={n}, triples", expected_result, it))

        # different lengths
        for n in self.lengths:
            if n > 3:  # smaller n give us an empty iterator, which causes issues
                data1 = list(range(n))
                data2 = [item * item for item in data1]
                data2 = data2[:-3]
                expected_result = list(zip(data1, data2))
                it = ZipIterator(NativeCheckpointableIterator(data1), NativeCheckpointableIterator(data2))
                self.test_cases.append((f"n={n}, different lengths", expected_result, it))


class TestPrefetchIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            for buffer_size in [42]:  # TODO: Add more buffer sizes after implementing lazy init for prefetcher
                data = list(range(n))
                it = PrefetchIterator(NativeCheckpointableIterator(data), buffer_size)
                self.test_cases.append((f"n={n}, buffer_size={buffer_size}", data, it))

    def test_zero_buffer_size(self):
        f = lambda: PrefetchIterator(NativeCheckpointableIterator([0]), buffer_size=0)
        self.assertRaises(ValueError, f)


class TestMultiplexIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    # TODO: Add test cases for behavior when source iterators end but item is retrieved
    def setUp(self):
        super().setUp()
        random = Random()
        random.seed(42)
        self.test_cases = []

        # two source iterators
        for n in self.lengths:
            indices = [random.randrange(0, 2) for _ in range(n)]
            data = [[2 * i + 0 for i in range(n)], [2 * i + 1 for i in range(n)]]
            data_copy = copy.deepcopy(data)
            expected_result = [data_copy[i].pop(0) for i in indices]
            it = MultiplexIterator(
                NativeCheckpointableIterator(indices), [NativeCheckpointableIterator(d) for d in data]
            )
            self.test_cases.append((f"n={n}, two source iterators", expected_result, it))

        # three source iterators
        for n in self.lengths:
            indices = [random.randrange(0, 3) for _ in range(n)]
            data = [[3 * i + 0 for i in range(n)], [3 * i + 1 for i in range(n)], [3 * i + 2 for i in range(n)]]
            data_copy = copy.deepcopy(data)
            expected_result = [data_copy[i].pop(0) for i in indices]
            it = MultiplexIterator(
                NativeCheckpointableIterator(indices), [NativeCheckpointableIterator(d) for d in data]
            )
            self.test_cases.append((f"n={n}, three source iterators", expected_result, it))


class TestNativeCheckpointableIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            data = list(range(n))
            expected_result = copy.deepcopy(data)
            it = NativeCheckpointableIterator(data)
            self.test_cases.append((f"n={n}", expected_result, it))

    def test_empty(self):
        it = NativeCheckpointableIterator([])
        self.assertRaises(StopIteration, it.__next__)

    def test_iterator_exception(self):
        self.assertRaises(ValueError, NativeCheckpointableIterator, iter(range(10)))


class TestFixedBatchIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            for batch_size in self.lengths:
                data = list(range(n))
                data_copy = copy.deepcopy(data)
                expected_result = []
                while data_copy:
                    expected_result.append(data_copy[:batch_size])
                    data_copy = data_copy[batch_size:]
                it = FixedBatchIterator(NativeCheckpointableIterator(data), batch_size=batch_size)
                self.test_cases.append((f"n={n}, batch_size={batch_size}", expected_result, it))

    def test_invalid_batch_size(self):
        f = lambda: FixedBatchIterator(NativeCheckpointableIterator([0]), batch_size=0)
        self.assertRaises(ValueError, f)


class TestRecurrentIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    @staticmethod
    def step_function(prev_state, item):
        output = prev_state + item
        return output, output

    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            data = list(range(n))
            expected_result = [data[0]]
            for i in data[1:]:
                expected_result.append(self.step_function(expected_result[-1], i)[1])
            it = RecurrentIterator(NativeCheckpointableIterator(data), self.step_function, initial_state=0)
            self.test_cases.append((f"n={n}", expected_result, it))


class TestSelectManyIterator(TestBase, TestFiniteIteratorMixin, TestFiniteIteratorCheckpointingMixin):
    @staticmethod
    def custom_selector(l):
        return [l[0]]

    def setUp(self):
        super().setUp()
        self.test_cases = []

        # default selector
        for n in self.lengths:
            for list_length in [1, 4, 9]:
                data = list(range(n))
                expected_result = copy.deepcopy(data)
                lists = []
                while data:
                    lists.append(data[:list_length])
                    data = data[list_length:]
                it = SelectManyIterator(NativeCheckpointableIterator(lists))
                self.test_cases.append((f"n={n}, list_length={list_length}, default selector", expected_result, it))

        # custom selector
        for n in self.lengths:
            for list_length in [4, 9]:
                data = list(range(n))
                expected_result = [item for i, item in enumerate(data) if (i % list_length) == 0]
                lists = []
                while data:
                    lists.append(data[:list_length])
                    data = data[list_length:]
                it = SelectManyIterator(NativeCheckpointableIterator(lists), collection_selector=self.custom_selector)
                self.test_cases.append((f"n={n}, list_length={list_length}, custom selector", expected_result, it))


class TestBlockwiseShuffleIterator(TestBase, TestFiniteIteratorCheckpointingMixin):
    def setUp(self):
        super().setUp()
        self.test_cases = []
        for n in self.lengths:
            for block_size in self.lengths:
                data = list(range(n))
                it = BlockwiseShuffleIterator(NativeCheckpointableIterator(copy.deepcopy(data)), block_size, self.seed)
                self.test_cases.append((f"n={n}, block_size={block_size}", data, it))

    def test_basic(self):
        for case_name, expected_result, it in self.test_cases:
            with self.subTest(case_name):
                result = list(it)
                self.assertMultisetEqual(result, expected_result)
