using BGGAPI.Src.Entities;

namespace BGGAPI.Src.Repositories.Interfaces;

public interface IBoardGameRepository
{
    Task<BoardGame?> GetByIdAsync(int id);
    Task<BoardGame?> GetCardByIdAsync(int id);
    Task<IEnumerable<BoardGame>> GetCardsByIdAsync(IEnumerable<int> ids);
}