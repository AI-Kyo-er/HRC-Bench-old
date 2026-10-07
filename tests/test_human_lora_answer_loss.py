import pytest


def test_tail_logits_preserve_answer_only_loss_and_parameter_gradients():
    torch=pytest.importorskip('torch')
    qwen=pytest.importorskip('transformers.models.qwen3.modeling_qwen3')
    from transformers import Qwen3Config
    torch.manual_seed(3)
    model=qwen.Qwen3ForCausalLM(Qwen3Config(vocab_size=64,hidden_size=32,intermediate_size=64,
        num_hidden_layers=1,num_attention_heads=4,num_key_value_heads=2,head_dim=8,attention_dropout=0.))
    model.eval();ids=torch.randint(0,64,(1,24));n=6
    labels=ids.clone();labels[:,:-n]=-100
    full=model(input_ids=ids,labels=labels,use_cache=False).loss;full.backward()
    gradients={name:p.grad.clone() for name,p in model.named_parameters() if p.grad is not None}
    model.zero_grad(set_to_none=True)
    tail=ids[:,-(n+1):].clone();tail[:,0]=-100
    kept=model(input_ids=ids,labels=tail,logits_to_keep=n+1,use_cache=False).loss;kept.backward()
    torch.testing.assert_close(full,kept,atol=1e-6,rtol=1e-6)
    for name,p in model.named_parameters():
        if name in gradients:torch.testing.assert_close(gradients[name],p.grad,atol=1e-6,rtol=1e-5)
