// Supply the missing legacy GNU hash specialization for 64-bit Windows size_t.
#include <cstdlib>
#include <ctime>
#include <ext/hash_map>
namespace __gnu_cxx {
template<> struct hash<unsigned long long> {
    size_t operator()(unsigned long long value) const {return static_cast<size_t>(value);}
};
}
