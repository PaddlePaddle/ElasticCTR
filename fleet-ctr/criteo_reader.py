#!/usr/bin/python
# Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# There are 13 integer features and 26 categorical features

class Dataset:
    def __init__(self):
        pass


class CriteoDataset(Dataset):
    def __init__(self, feature_names):
        self.feature_names = feature_names
        self.feature_dict = {}
        for idx, name in enumerate(self.feature_names):
            self.feature_dict[name] = idx

    def _reader_creator(self, file_list, is_train, trainer_num, trainer_id):
        hash_dim_ = int(os.environ['SPARSE_DIM'])
        def reader():
            for file in file_list:
                with open(file, 'r') as f:
                    line_idx = 0
                    for line in f:
                        line_idx += 1
                        feature = line.rstrip('\n').split()
                        features = []
                        for i in range(len(self.feature_names)):
                            features.append([])
                        label = feature[1]
                        for fea_pair in feature[2:]:
                            #print(fea_pair)
                            tmp_list = fea_pair.split(":")
                            feasign, slot = tmp_list[0], tmp_list[1]
                            if slot not in self.feature_dict:
                                continue
                            features[self.feature_dict[slot]].append(int(feasign) % hash_dim_)
                        for i in range(len(features)):
                            if features[i] == []:
                                features[i].append(0)
                        features.append([label])
                        yield features

        return reader

    def train(self, file_list, trainer_num, trainer_id):
        return self._reader_creator(file_list, True, trainer_num, trainer_id)

    def test(self, file_list):
        return self._reader_creator(file_list, False, 1, 0)

    def infer(self, file_list):
        return self._reader_creator(file_list, False, 1, 0)
