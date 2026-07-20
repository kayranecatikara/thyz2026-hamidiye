// LibTorch CUDA sağlık testi — FAZ 4 doğrulaması + yarışma günü hızlı kontrol.
// Beklenen: CUDA available: true, cuDNN true, GPU'da matmul sonucu sonlu bir sayı.
#include <torch/torch.h>
#include <iostream>

int main() {
    std::cout << "LibTorch surumu: " << TORCH_VERSION << std::endl;

    const bool cuda = torch::cuda::is_available();
    std::cout << "CUDA available: " << (cuda ? "true" : "false") << std::endl;
    if (!cuda) {
        std::cerr << "HATA: CUDA gorulmedi!" << std::endl;
        return 1;
    }
    std::cout << "cuDNN available: "
              << (torch::cuda::cudnn_is_available() ? "true" : "false") << std::endl;
    std::cout << "GPU sayisi: " << torch::cuda::device_count() << std::endl;

    // Tensörü GPU'ya taşı ve gerçek bir işlem çalıştır
    auto t = torch::rand({1024, 1024});
    auto tg = t.to(torch::kCUDA);
    auto sum = tg.matmul(tg).sum();
    std::cout << "Tensor cihazi: " << tg.device() << std::endl;
    std::cout << "GPU matmul toplami: " << sum.item<float>() << std::endl;

    if (!std::isfinite(sum.item<float>())) {
        std::cerr << "HATA: GPU hesabi gecersiz deger dondurdu!" << std::endl;
        return 2;
    }
    std::cout << "TORCH_CUDA_TEST_OK" << std::endl;
    return 0;
}
