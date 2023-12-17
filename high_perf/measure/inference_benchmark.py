import torch
from high_perf.common.data.gsmk_dataset import get_data_loader
import time
import fire
from torch.profiler import profile, record_function, ProfilerActivity


from llama import Llama
from typing import List

### Setup ###
BATCH_SIZE = 16
BATCH_COUNT = 5
NUM_WORKERS = 1
PROFILE_MEMORY = True

# https://huggingface.co/datasets/gsm8k
HUGGING_FACE_GSMK_DATASET_ID = "gsm8k"

# Manual seed for reproducatibility
SEED = 42
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)

DEVICE_CUDA = 'cuda'
DEVICE_CPU = 'cpu'


def get_device():
    return torch.device(DEVICE_CUDA if torch.cuda.is_available() else DEVICE_CPU)

def get_model(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size):
    generator = Llama.build(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
    )
    return generator


def run_benchmark(dataloader, model):
    load_time_per_batch = torch.zeros(BATCH_COUNT)
    inference_time_per_batch = torch.zeros(BATCH_COUNT)
    total_time_per_batch = torch.zeros(BATCH_COUNT)
    
    device = get_device()
    # model.to(device)
    print("Working on device: {}".format(device))
    
    
    for batch_idx in range(BATCH_COUNT):
        print("Starting BATCH {} of {}".format(batch_idx + 1, BATCH_COUNT))
        (output, load_time, inference_time), batch_time = measure_runtime(run_batch_inference,
                                                              dataloader,
                                                              model)
        load_time_per_batch[batch_idx] = load_time
        inference_time_per_batch[batch_idx] = inference_time
        total_time_per_batch[batch_idx] = batch_time

        print("Finished Batch {} of {}".format(batch_idx + 1, BATCH_COUNT))
        print("Batch load time: {}".format(load_time))
        print("Batch inference time: {}".format(inference_time))
        print("Batch total time: {}".format(batch_time))
    return model, load_time_per_batch, inference_time_per_batch, total_time_per_batch


def measure_runtime(func, *func_args):
    start = time.perf_counter()
    result = func(*func_args)
    end = time.perf_counter()
    elapsed = end - start
    return result, elapsed


def run_batch_inference(dataloader, model):
    (question, answer), load_time = measure_runtime(
        __get_next_batch, dataloader)

    
    # print("question: ", question, "\nanswer: ", answer)
    # print("question type: ", type(question), "answer type", type(answer))
    # print("question shape: ", len(question), "answer shape", len(answer))
    # device = get_device()
    # x = x.to(device)
    # y = y.to(device)

    output, inference_time = measure_runtime(
        inference,
        model,
        [question])
    
    return output, load_time, inference_time

def inference(
    generator: Llama,
    prompts: List[str],
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_gen_len: int = 64,
):
    with torch.no_grad():
        results = generator.text_completion(
            prompts,
            max_gen_len=max_gen_len,
            temperature=temperature,
            top_p=top_p,
        )
        return zip(prompts, results)

def __get_next_batch(dataloader):
    return next(iter(dataloader))


def benchmark(ckpt_dir, 
              tokenizer_path, 
              max_seq_len, 
              max_batch_size,
              batch_size=BATCH_SIZE,
              num_workers=NUM_WORKERS):
    print("Starting up...")

    print("Building data loaders...")
    data_loader = get_data_loader(num_workers, batch_size)

    print("Initializing Model...")
    net = get_model(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size)

    print("Running inference benchmark...\n")
    
    with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], record_shapes=True, profile_memory=PROFILE_MEMORY) as prof:
        with record_function("run_benchmark"):
        #     _, load, inference, total = run_benchmark(data_loader, net)
            _, load, inference, total = run_benchmark(data_loader, net)
    
    print("\n\n Manual Profile Results...")
    print("Data-loading times")
    print("> per epoch: ", load)
    print("> average: ", torch.mean(load))
    print("\nInference time for each epoch")
    print("> per epoch", inference)
    print("> average", torch.mean(inference))
    print("\nTotal time for each epoch")
    print("> per epoch", total)
    print("> average", torch.mean(total))

    print("\n\n")
    print("Profiling sorted by CUDA time total")
    profile_cuda_time = prof.key_averages().table(sort_by="cuda_time_total", row_limit=10)
    print(profile_cuda_time)

    print("\n\n")
    print("Profiling sorted by CUDA memory usage")
    profile_cuda_mem = prof.key_averages().table(sort_by="self_cuda_memory_usage", row_limit=10)
    print(profile_cuda_mem)


if __name__ == "__main__":
    # torch.cuda.empty_cache()
    fire.Fire(benchmark)
