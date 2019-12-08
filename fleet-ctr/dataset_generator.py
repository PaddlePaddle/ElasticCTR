#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
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

import paddle.fluid.incubate.data_generator as dg
import os
hash_dim_ = int(os.environ['SPARSE_DIM'])
categorical_range_ = range(14, 40)

class DacDataset(dg.MultiSlotDataGenerator):
    """
    DacDataset: inheritance MultiSlotDataGeneratior, Implement data reading
    Help document: http://wiki.baidu.com/pages/viewpage.action?pageId=728820675
    """

    def set_config(feature_names):
        self.feature_names = feature_names
        assert len(feature_names) < len(categorical_range_)

    def generate_sample(self, line):
        """
        Read the data line by line and process it as a dictionary
        """

        def reader():
            """
            This function needs to be implemented by the user, based on data format
            """
            features = line.rstrip('\n').split('\t')
            sparse_feature = []
            for idx in categorical_range_[:len(self.feature_names)]:
                sparse_feature.append(
                    [hash(str(idx) + features[idx]) % hash_dim_])
            label = [int(features[0])]
            feature_name = []
            for i, idx in enumerate(categorical_range_[:len(self.feature_names)]):
                feature_name.append(self.feature_names[i])
            feature_name.append("label")

            yield zip(feature_name, sparse_feature + [label])

        return reader


d = DacDataset()
feature_names = []
with open(sys.argv[1]) as fin:
    for line in fin:
        feature_names.append(line.strip())
d.set_config(feature_names)
d.run_from_stdin()
