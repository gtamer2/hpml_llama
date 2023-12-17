import torch
import fire
from llama import Llama

def get_model(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size):
    generator = Llama.build(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
    )
    return generator

def script_transformer_blocks(ckpt_dir, 
              tokenizer_path, 
              max_seq_len, 
              max_batch_size):
    print("Starting up...")
    torch.cuda.empty_cache()

    print("Initializing Model...")
    llama = get_model(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size)
    transformer_blocks = llama.model.layers

    print("Attempting to script model...")
    # scripted_blocks = []
    for idx, transformer_block in enumerate(transformer_blocks):
        print(f"Scripting transformer block {idx}/{len(transformer_blocks)}...")
        transformer_block.eval()
        # scripted_block = torch.jit.script(transformer_block)
        print("Scripting attention.wq")
        transformer_block.attention.wq = torch.jit.script(transformer_block.attention.wq)
        print("Scripting attention.wk")
        transformer_block.attention.wk = torch.jit.script(transformer_block.attention.wk)
        print("Scripting attention.wv")
        transformer_block.attention.wv = torch.jit.script(transformer_block.attention.wv)
        print("Scripting attention.wo")
        transformer_block.attention.wo = torch.jit.script(transformer_block.attention.wo)
        print("Scripting attention_norm")
        transformer_block.attention_norm = torch.jit.script(transformer_block.attention_norm)

    print("Successfully scripted the transformer blocks of the model!")
    print("Saving scripted model...")
    llama.save("scripted_llama.pt")


if __name__ == "__main__":
    fire.Fire(script_transformer_blocks)